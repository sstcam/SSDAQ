import unittest

from ssdaq.core.SSDataListener import SSDataListener
import socket
from queue import Queue
import time
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
       print('Sent data: %s'%data)
       print('Recieved data: %s'%data_recv[1])
       udp_sock.close()
       self.assertTrue(data==data_recv[1])


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

if (__name__ == '__main__'):
           unittest.main()
