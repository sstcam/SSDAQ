import unittest

from ssdaq.core.SSDataListener import SSDataListener
import socket
from queue import Queue
import time

#Silencing INFO logging
import logging
from ssdaq import sslogger
sslogger.setLevel(logging.ERROR)

class TestDataListener(unittest.TestCase):

    def test_recv_data(self):
        adr = '127.0.0.1'
        port = 61610
        queue = Queue()
        listener = SSDataListener(port,queue)
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = b'123456789'
        listener.start()
        time.sleep(0.5)
        udp_sock.sendto(data, (adr,port))
        data_recv = queue.get()
        listener.running = False
        udp_sock.sendto(data, (adr,port))
        data_recv = queue.get()
        listener.join()
        udp_sock.close()
        self.assertTrue(data==data_recv[1],'Recieved data equal to sent data')

from ssdaq.core.SSEventBuilder import SSEvent
import numpy as np
class TestSSEvent(unittest.TestCase):
    def test_pack_unpack(self):
        event1 = SSEvent(timestamp = 12345,event_number=1234,run_number=123)
        event1.data[2,:] = np.arange(64)
        event1.data[3,:] = np.arange(64)
        event1.timestamps[:,0] = np.arange(32,dtype=np.uint64)
        packed_event = event1.pack()
        event2 = SSEvent()
        event2.unpack(packed_event)

        self.assertEqual(event1.event_number , event2.event_number)
        self.assertEqual(event1.run_number , event2.run_number)
        self.assertEqual(event1.event_timestamp , event2.event_timestamp)
        self.assertTrue((event1.data[2]==event2.data[2]).all())
        self.assertTrue((event1.data[3]==event2.data[3]).all())
        self.assertFalse((event1.data[4]==event2.data[4]).all())
        self.assertTrue(np.isnan(event1.data[4,0]))
        self.assertTrue((event1.timestamps[0]==event2.timestamps[0]).all())


from ssdaq.core.SSEventBuilder import SSEventBuilder
class TestSSEventBuilder(unittest.TestCase):
    
    def test_out_of_range_ip(self):
        sslogger.setLevel(logging.FATAL)
        import numpy as np
        import struct
        builder = SSEventBuilder()
        try:    
            builder.start()
            data_packet = bytearray()
            data_packet.extend(struct.pack('>Q',192093))
            data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
            data_packet.extend(struct.pack('>Q',192093))
            data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
            builder.data_queue.put(('192.168.0.132',data_packet))
            builder.running = False
            builder.data_queue.put(('192.168.0.132',data_packet))
            builder.join()        
        except :
            self.assertTrue(True)
        else:
            self.assertTrue(False,'IP out of range not allowed without relaxed_ip_range set to True')

        builder = SSEventBuilder(relaxed_ip_range = True)
        try:    
            builder.start()
            data_packet = bytearray()
            data_packet.extend(struct.pack('>Q',192093))
            data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
            data_packet.extend(struct.pack('>Q',192093))
            data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
            builder.data_queue.put(('192.168.0.132',data_packet))
            builder.running = False
            builder.data_queue.put(('192.168.0.132',data_packet))
            builder.join()        
        except :
            self.assertTrue(False,'IP out of range allowed with relaxed_ip_range set to True')
        else:
            self.assertTrue(True)

        sslogger.setLevel(logging.ERROR)

if (__name__ == '__main__'):
           unittest.main()
