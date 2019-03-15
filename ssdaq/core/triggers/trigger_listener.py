import asyncio
import struct
import numpy as np
from datetime import datetime,timedelta
import zmq
import zmq.asyncio
from distutils.version import LooseVersion
from chec import checlogger
if(LooseVersion('17')>LooseVersion(zmq.__version__)):
    zmq.asyncio.install()


class TriggerPacketProtocol(asyncio.Protocol):
    def __init__(self,loop,log, packet_debug_stream_file = None):
        self.buffer = asyncio.Queue()
        self.loop = loop
        self.log = log.getChild('TriggerPacketProtocol')

    def connection_made(self, transport):
        self.log.info('Connected to port')
        self.transport = transport

    def datagram_received(self, data, addr):
        cpu_time = datetime.utcnow()
        self.buffer.put_nowait((data, addr))




class TriggerPacketListener:
    def __init__(self,ip:str,port:int,publishers:list):
        self.loop = asyncio.get_event_loop()
        self.log = checlogger.getChild("TriggerPacketListener")
        self.running = True
        self.publishers = publishers
        self.listen_addr = (ip,port)
        self.corrs = [self.relay]
        self.loop = asyncio.get_event_loop()
        self.tpp = TriggerPacketProtocol(self.loop,self.log)
        for p in self.publishers:
            p.give_loop(self.loop)

    def run(self):
        self.log.info('Settting up listener at %s:%d'%(tuple(self.listen_addr)))
        listen = self.loop.create_datagram_endpoint(
                lambda :SlowSignalDataProtocol(self.loop,self.log),
                local_addr=self.listen_addr)

        ransport, protocol = self.loop.run_until_complete(listen)
        self.ss_data_protocol = protocol
        self.log.info('Number of publishers registered %d'%len(self.publishers))
        for c in self.corrs:
            self.loop.create_task(c)

        try:
            self.loop.run_forever()
        except:
            pass
        self.loop.close()

    async def relay(self):
        while(self.running):
            packet = await self.tpp.buffer.get()
            for pub in self.publishers:
                pub.publish(packet[0])




