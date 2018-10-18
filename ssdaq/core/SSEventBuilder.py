from queue import Queue
from threading import Thread
import numpy as np
import struct

class DataStream(bytearray):
    '''
    Helper class to create an arbitrary byte stream
    '''
    def append(self, v, fmt='>B'):
        self.extend(struct.pack(fmt, v))

class SSEvent(object):
    """
    A class representing a slow signal event
    """

    def __init__(self,timestamp=0,event_number = 0,run_number = 0):
        
        self.event_number = event_number
        self.run_number = run_number
        self.event_timestamp = timestamp
        self.data = np.empty((32,64))
        self.data[:] = np.nan
        #store also the time stamps for the individual readings 
        #two per TM (primary and aux)
        self.timestamps = np.zeros((32,2),dtype=np.uint64)
    
    def pack(self):
        '''
        Convinience method to pack the event into a bytestream
        '''
        d_stream = DataStream()

        d_stream.append(self.event_number,'Q')
        d_stream.append(self.run_number,'Q')
        d_stream.append(self.event_timestamp,'Q')
        for v in self.data.ravel():
                d_stream.append(v,'d')
        for v in self.timestamps.ravel():
                d_stream.append(v,'Q')
        return d_stream

    def unpack(self,byte_stream):
        '''
        Unpack a bytestream into an event
        '''
        self.event_number, self.run_number,self.event_timestamp = struct.unpack_from('3Q',byte_stream,0)
        self.data = np.asarray(struct.unpack_from('2048d',byte_stream,8*3)).reshape(32,64)
        self.timestamps = np.asarray(struct.unpack_from('64Q',byte_stream,8*3+8*2048)).reshape(32,2)


READOUT_LENGTH = 64*2+2*8
class SSEventBuilder(Thread):
    """ 
    Slow signal event builder. Constructs 
    slow signal events from data packets recieved from 
    Target Modules.
    """
    def __init__(self,verbose=False):
        Thread.__init__(self)
        self.data_queue = Queue()
        self.event_queue = Queue()

        self.inter_data = {}
        self.inter_queue_lengths = np.zeros(32,dtype = np.uint64)
        self.next_ts = np.zeros(32,dtype = np.uint64)
        #assume we always have 32 modules
        for i in range(32):
            self.inter_data[i] = []
        
        self.running = False
        self.event_tw = int(0.05*1e9)
        self.nprocessed_packets = 0
        self.nconstructed_events = 1
        self.packet_counter = {}
        self.event_counter = {}
        self.verbose = verbose
        self.pot_ev = True
    def _build_event(self):
        #updating latest timestamps for a potential event
        for k,v in self.inter_data.items():
            self.inter_queue_lengths[k] =  len(v)
            if(len(v)>2):
                self.next_ts[k] = v[0][0]
            else:
                self.next_ts[k] = 0

        #Data from one TM is enough for an event
        if((np.sum(self.next_ts>0)>0)  
            &(np.max(self.inter_queue_lengths)>1)  
            &(np.mean(self.inter_queue_lengths)>2) 
            ):

            #find all data that is within the event tw of the
            #earliest time stamp
            earliest_ts = np.min(self.next_ts[self.next_ts>0])
            m = ((self.next_ts-earliest_ts) < self.event_tw) & ((self.next_ts-earliest_ts)>=0)
            
            #construct event
            event = SSEvent(int(np.mean(self.next_ts[m])),self.nconstructed_events,1)
            for k in np.where(m)[0]:
                if(k in self.event_counter):
                    self.event_counter[k] += 1
                else:
                    self.event_counter[k] = 1
                #put data into a temporary array of uint type
                tmp_data = self.inter_data[k].pop(0)[1]
                tmp_array = np.empty(64,dtype=np.uint64)
                tmp_array[:32] = tmp_data[1:33]
                tmp_array[32:] = tmp_data[34:]
                
                #converting counts to mV
                m = tmp_array < 0x8000
                tmp_array[m] += 0x8000
                tmp_array[~m] = tmp_array[~m]&0x7FFF
                event.data[k] = tmp_array* 0.03815*2.
                #get the readout time stamps for the primary and aux
                event.timestamps[k][0]=tmp_data[0]
                event.timestamps[k][1]=tmp_data[33]
                

            self.event_queue.put(event)
            self.nconstructed_events += 1
        else:
            self.pot_ev = False
    def run(self):
        self.running = True
        self.setName('SSEventBuilder')
        last_nevents = 0
        
        while(self.running):
            
            while(not self.data_queue.empty() or not self.pot_ev):
                self.pot_ev = True
                data = self.data_queue.get()
                nreadouts = int(len(data[1])/(READOUT_LENGTH))
                if(len(data[1])%(READOUT_LENGTH) != 0):
                    print("Warning: Got unsuported packet size")
                
                
                module_nr = int(data[0][-2:])
                if(self.verbose):
                    print("Got data from %s"%(str(data[0])))
                    print("Module number %d "%(module_nr))
                
                for i in range(nreadouts):
                    unpacked_data = struct.unpack_from('Q32H'+'Q32H',data[1],i*(64*2+2*8))
                    self.inter_data[module_nr].append((unpacked_data[0],unpacked_data))
                
                if(module_nr in self.packet_counter):
                    self.packet_counter[module_nr] +=1
                else:
                    self.packet_counter[module_nr] =1
                
                self.nprocessed_packets += 1

            self._build_event()
            
            if(self.nprocessed_packets>last_nevents and self.verbose):
                print("Processed packets %d, Constructed events: %d"%(self.nprocessed_packets,self.nconstructed_events))
                last_nevents = self.nprocessed_packets
                print(self.packet_counter)
                print(self.event_counter)
                # print('Buffer lengths %d %d'%(self.data_queue.qsize(),self.event_queue.qsize()))







