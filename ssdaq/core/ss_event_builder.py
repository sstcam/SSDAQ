import asyncio
import socket
import struct
import numpy as np
READOUT_LENGTH = 64*2+2*8 #64 2-byte channel amplitudes and 2 8-byte timestamps

class SlowSignalDataProtocol(asyncio.Protocol):
    def __init__(self,loop,log):
        self._buffer = asyncio.Queue()
        self.loop = loop
        self.log = log.getChild('SlowSignalDataProtocol')

    def connection_made(self, transport):
        self.log.info('Connected to port')
        self.transport = transport

    def datagram_received(self, data, addr):
        
        if(len(data)%(READOUT_LENGTH) != 0):
            self.log.warn("Got unsuported packet size, skipping packet")
            self.log.info("Bad package came from %s:%d"%tuple(data[0]))
            return
        nreadouts = int(len(data)/(READOUT_LENGTH))

        #getting the module number from the last two digits of the ip
        ip = addr[0]
        module_nr = int(ip[-ip[::-1].find('.'):])%100
        if(module_nr>31 and self.relaxed_ip_range):
            #ensure that the module number is in the allowed range
            #(mostly important for local or standalone setups simulations)
            module_nr = module_nr%32
            self.log.debug('Got data from ip %s which is outsie the allowed range'%ip)
        elif(module_nr>31):
            self.log.error('Error: got packets from ip out of range:')
            self.log.error('   %s'%ip)
            self.log.error('This can be supressed if relaxed_ip_range=True')
            raise RuntimeError
            
        self.log.debug("Got data from %s assigned to module %d"%(str(ip),module_nr))
        for i in range(nreadouts):
            unpacked_data = struct.unpack_from('>Q32HQ32H',data,i*(READOUT_LENGTH))
            self.loop.create_task(self._buffer.put((module_nr,unpacked_data[0],unpacked_data)))
        self.log.debug('Front buffer length %d'%(self._buffer.qsize()))
        if(self._buffer.qsize()>1000):
            self.log.warning('Front buffer length %d'%(self._buffer.qsize()))

class PartialEvent:
    int_counter = 0
    def __init__(self,tm_num,data):
        self.data = [None]*32
        self.data[tm_num] = data
        self.timestamp =data[0]
        self.tm_parts = [0]*32
        self.tm_parts[tm_num] = 1
        PartialEvent.int_counter += 1
        self.event_number =  PartialEvent.int_counter   
    def add_part(self, tm_num, data):
        self.data[tm_num] = data
        self.tm_parts[tm_num] = 1


class SSEventBuilder:
    def __init__(self, relaxed_ip_range=False, event_tw = int(0.0001*1e9), listen_addr=('0.0.0.0', 2009), publishers = []):
        from ssdaq import sslogger
        self.log = sslogger.getChild('SSEventBuilder')
        self.relaxed_ip_range = relaxed_ip_range
        # self.listening = 
        # self.building_events = 
        # self.publishing_events = 

        self.listen_addr = listen_addr

        #settings 
        self.event_tw = event_tw

        #counters
        self.nprocessed_packets = 0
        self.nconstructed_events = 1
        self.packet_counter = {}
        self.event_counter = {}

        self.loop = asyncio.get_event_loop()
        self.corrs = [self.builder()]
    
        #buffers
        self.buffer_len = 10000
        self.inter_buff = []
        self.partial_ev_buff = asyncio.queues.collections.deque(maxlen=self.buffer_len)
        
        self.publishers = publishers 
    
    def run(self):
        self.log.info('Settting up listener at %s:%d'%(tuple(self.listen_addr)))
        listen = self.loop.create_datagram_endpoint(
        lambda :SlowSignalDataProtocol(self.loop,self.log), local_addr=self.listen_addr)
        transport, protocol = self.loop.run_until_complete(listen)
        self.ss_data_protocol = protocol
        for c in self.corrs:
            self.loop.create_task(c)

        try:
            self.loop.run_forever()
        except:
            pass
        self.loop.close()

    async def builder2(self):
        import collections
        self.log.info('Starting event build loop')
        for i in range(32):
            self.inter_buff.append(collections.deque(maxlen=self.buffer_len))

        while(True):
            b_sizes = []
            for ib in self.inter_buff:
                b_sizes.append(len(ib))
            if(max(b_sizes)<150 and self.ss_data_protocol._buffer.qsize()>2):
                while(self.ss_data_protocol._buffer.qsize()>1):
                    packet = await self.ss_data_protocol._buffer.get()        
                    self.inter_buff[packet[0]].append(packet[2])
            elif(max(b_sizes)<150 and self.ss_data_protocol._buffer.qsize()==0):
                packet = await self.ss_data_protocol._buffer.get()        
                self.inter_buff[packet[0]].append(packet[2])
            else:
                packet = await self.ss_data_protocol._buffer.get()        
                self.inter_buff[packet[0]].append(packet[2])
            b_sizes = []
            for ib in self.inter_buff:
               b_sizes.append(len(ib))
            if(max(b_sizes)<150):
                continue

            timestamps = []#[(-1,-1)]*32
            for i,ib in enumerate(self.inter_buff):
                if(len(ib)>0):  
                    timestamps.append((i,ib[0][0]))
            timestamps = sorted(timestamps,key=lambda x: x[1])

            t0 = timestamps[0][1]
            pqkt = self.inter_buff[timestamps[0][0]].popleft()
            pe = PartialEvent(timestamps[0][0],pqkt)
            for t in timestamps[1:]:
                if(t[0]==-1):
                    continue
                if(t[1]-t0>=self.event_tw):
                    break
                pqkt = self.inter_buff[t[0]].popleft()
                pe.add_part(t[0],pqkt)

            event = self.build_event(pe)               
            if(self.nconstructed_events%100==0):
                self.log.info('Built event %d'%self.nconstructed_events)
                self.log.info('Number of TMs participating %d'%(sum(event.timestamps[:,0]>0)))
            self.log.debug('Built event %d'%self.nconstructed_events)
            for pub in self.publishers:
                pub.publish(event)

    async def builder(self):
        self.log.info('Starting event build loop')
        packet = await self.ss_data_protocol._buffer.get()
        self.partial_ev_buff.append(PartialEvent(packet[0], packet[2]))
        while(True):
            packet = await self.ss_data_protocol._buffer.get()
            self.log.debug('Got packet from front buffer with timestamp %f and tm id %d'%(packet[1]*1e-9,packet[0]))
            pe = self.partial_ev_buff[-1]
            dt = (pe.timestamp - packet[1])

            if(abs(dt) < self.event_tw  and pe.tm_parts[packet[0]] == 0):#
                self.partial_ev_buff[-1].add_part(packet[0], packet[2])
                self.log.debug('Packet added to the tail of the buffer')
            
            elif(dt<0):
                self.partial_ev_buff.append(PartialEvent(packet[0], packet[2]))
                self.log.debug('Packet added to a new event at the tail of the buffer')
            
            else:
                if(self.partial_ev_buff[0].timestamp - packet[1]>0):
                    self.partial_ev_buff.appendleft(PartialEvent(packet[0], packet[2]))
                    self.log.debug('Packet added to a new event at the head of the buffer')   
                else:
                    self.log.debug('Finding right event in buffer')
                    found = False
                    for i in range(len(self.partial_ev_buff)-1,0,-1):
                        pe = self.partial_ev_buff[i]
                        dt = (pe.timestamp - packet[1])

                        if(abs(dt)< self.event_tw):#
                            if(pe.tm_parts[packet[0]]==1):
                                self.log.warning('Dublette packet with timestamp %f and tm id %d with cpu timestamp %f'%(packet[1]*1e-9,packet[0],packet[2][33]*1e-9))
                            self.partial_ev_buff[i].add_part(packet[0], packet[2]) 
                            self.log.debug('Packet added to %d:th event in buffer'%i)
                            found =True
                            break
                        elif(dt<0):
                            self.partial_ev_buff.insert(i+1,PartialEvent(packet[0], packet[2]))
                            found = True
                            break
                            
                    if(not found):
                        self.log.warning('No partial event found for packet with timestamp %f and tm id %d'%(packet[1]*1e-9,packet[0]))
                        self.log.info('Newest event timestamp %f'%(self.partial_ev_buff[-1].timestamp*1e-9))
                        self.log.info('Next event timestamp %f'%(self.partial_ev_buff[0].timestamp*1e-9))     
            if(self.partial_ev_buff[-1].timestamp - self.partial_ev_buff[0].timestamp>(2*1e9)):

                event = self.build_event(self.partial_ev_buff.popleft())               
                if(self.nconstructed_events%10==0):
                    # for d in self.partial_ev_buff:
                        # print(d.timestamp*1e-9,d.timestamp,d.event_number, d.tm_parts)
                    self.log.info('Built event %d'%self.nconstructed_events)
                    self.log.info('Newest event timestamp %f'%self.partial_ev_buff[-1].timestamp)
                    self.log.info('Next event timestamp %f'%self.partial_ev_buff[0].timestamp)
                    self.log.info('Last timestamp dt %f'%((self.partial_ev_buff[-1].timestamp - self.partial_ev_buff[0].timestamp)*1e-9))
                    self.log.info('Number of TMs participating %d'%(sum(event.timestamps[:,0]>0)))
                    self.log.info('Buffer lenght %d'%(len(self.partial_ev_buff)))
                self.log.debug('Built event %d'%self.nconstructed_events)
                for pub in self.publishers:
                    pub.publish(event)
    
    def build_event(self,pe):
        from SSEventBuilder import SSEvent
        #construct event
        event = SSEvent(int(pe.timestamp),self.nconstructed_events,0)
        for i,tmp_data in enumerate(pe.data):
            if(tmp_data == None):
                continue
            if(i in self.event_counter):
                self.event_counter[i] += 1
            else:
                self.event_counter[i] = 1
            #put data into a temporary array of uint type
            tmp_array = np.empty(64,dtype=np.uint64)
            tmp_array[:32] = tmp_data[1:33]
            tmp_array[32:] = tmp_data[34:]
            
            #converting counts to mV
            m = tmp_array < 0x8000
            tmp_array[m] += 0x8000
            tmp_array[~m] = tmp_array[~m]&0x7FFF
            event.data[i] = tmp_array* 0.03815*2.
            #get the readout time stamps for the primary and aux
            event.timestamps[i][0]=tmp_data[0]
            event.timestamps[i][1]=tmp_data[33]
        self.nconstructed_events += 1
        return event    


class ZMQEventPublisher():
    def __init__(self,port,ip,loop = None):
        import zmq
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.PUB)
        con_str = 'tcp://%s:'%ip+str(port)
        self.sock.bind(con_str)
        self.log = logging.getLogger('ssdaq.SSEventDataPublisher')
        self.log.info('Initialized event publisher on: %s'%con_str)
    def publish(self,event):
        self.sock.send(event.pack())

if __name__ == "__main__":
    from ssdaq import sslogger
    import logging
    import os
    from subprocess import call
    call(["taskset","-cp", "0,4","%s"%(str(os.getpid()))])
    sslogger.setLevel(logging.INFO)
    zmq_pub = ZMQEventPublisher(5555,'127.0.0.101') 
    ev_builder = SSEventBuilder(publishers= [zmq_pub])
    ev_builder.run()

