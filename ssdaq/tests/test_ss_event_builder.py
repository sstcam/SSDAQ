import unittest

from ssdaq import SSReadout,SSReadoutAssembler#,SSReadoutlowSignalDataProtocol

import socket
from queue import Queue
import time

#Silencing INFO logging
import logging
from ssdaq import sslogger
sslogger.setLevel(logging.ERROR)

import numpy as np
class TestSSReadout(unittest.TestCase):
    def test_pack_unpack(self):
        readout1 = SSReadout(timestamp = 12345,readout_number=1234)
        readout1.data[2,:] = np.arange(64)
        readout1.data[3,:] = np.arange(64)
        readout1.timestamps[:,0] = np.arange(32,dtype=np.uint64)
        packed_readout = readout1.pack()
        readout2 = SSReadout()
        readout2.unpack(packed_readout)

        self.assertEqual(readout1.readout_number , readout2.readout_number)
        self.assertEqual(readout1.readout_timestamp , readout2.readout_timestamp)
        self.assertTrue((readout1.data[2]==readout2.data[2]).all())
        self.assertTrue((readout1.data[3]==readout2.data[3]).all())
        self.assertFalse((readout1.data[4]==readout2.data[4]).all())
        self.assertTrue(np.isnan(readout1.data[4,0]))
        self.assertTrue((readout1.timestamps[0]==readout2.timestamps[0]).all())


# from ssdaq.core.SSReadoutAssembler import SSReadoutAssembler
# class TestSSReadoutAssembler(unittest.TestCase):
    
#     def test_out_of_range_ip(self):
#         sslogger.setLevel(logging.FATAL)
#         import numpy as np
#         import struct
#         builder = SSReadoutAssembler()
#         try:    
#             builder.start()
#             data_packet = bytearray()
#             data_packet.extend(struct.pack('>Q',192093))
#             data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
#             data_packet.extend(struct.pack('>Q',192093))
#             data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
#             builder.data_queue.put(('192.168.0.132',data_packet))
#             builder.running = False
#             builder.data_queue.put(('192.168.0.132',data_packet))
#             builder.join()        
#         except :
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False,'IP out of range not allowed without relaxed_ip_range set to True')

#         builder = SSReadoutAssembler(relaxed_ip_range = True)
#         try:    
#             builder.start()
#             data_packet = bytearray()
#             data_packet.extend(struct.pack('>Q',192093))
#             data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
#             data_packet.extend(struct.pack('>Q',192093))
#             data_packet.extend(struct.pack('>32H',*np.arange(32,dtype=np.uint16)))
#             builder.data_queue.put(('192.168.0.132',data_packet))
#             builder.running = False
#             builder.data_queue.put(('192.168.0.132',data_packet))
#             builder.join()        
#         except :
#             self.assertTrue(False,'IP out of range allowed with relaxed_ip_range set to True')
#         else:
#             self.assertTrue(True)

#         sslogger.setLevel(logging.ERROR)

if (__name__ == '__main__'):
           unittest.main()
