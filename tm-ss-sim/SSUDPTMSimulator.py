import socket
import os
import numpy as np
import time
from datetime import datetime

import struct

class DataStream(bytearray):
    def append(self, v, fmt='>B'):
        self.extend(struct.pack(fmt, v))

class TMSimulator(object):
	def __init__(self, port, ip):
		self.port = port
		self.host_ip = ip
		self.data_prim = np.random.uniform(0,400,32)
		self.data_aux = np.random.uniform(0,400,32)

	def simulate_data(self):
		#simulate next step
		self.data_prim += np.random.uniform(-4,4,32)
		self.data_prim[self.data_prim<0] = 0
		self.data_aux += np.random.uniform(-4,4,32)
		self.data_aux[self.data_aux<0] = 0
		
		#convert mV to counts and correct bit format
		prim_counts = np.asarray(self.data_prim/(0.03815*2.),dtype=np.uint16)
		m = prim_counts<0x8000
		prim_counts[m] +=0x8000
		prim_counts[~m]= prim_counts[~m]&0x7FFF
		aux_counts = np.asarray(self.data_aux/(0.03815*2.),dtype=np.uint16)
		m = aux_counts<0x8000
		aux_counts[m] +=0x8000
		aux_counts[~m]= aux_counts[~m]&0x7FFF
		return prim_counts.copy(),aux_counts.copy()

	def Run(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		
		server_address = (self.host_ip, port)
		npackets = 0
		nreading = 0
		
		t = datetime.utcnow()
		while(True):
			timestamp = t.timestamp()	+ np.random.uniform(-2e-4,2e-4)
			data_packet = DataStream()
			for i in range(10):
				prim, aux = self.simulate_data()
				data_packet.append(int((timestamp+0.1*i)*1e9),'Q')
				for ss_p in prim:
					data_packet.append(ss_p,'H')
				data_packet.append(int((timestamp+0.1*i)*1e9),'Q')
				for ss_a in aux:
					data_packet.append(ss_a,'H')
				nreading += 1

			sent = sock.sendto(data_packet, server_address)
			if(npackets%10==0):
				print("Sent %d packets"%(npackets))
				print(len(data_packet))
			npackets +=1
			t = datetime.utcnow()
			sleeptime = 1.0 - (t.microsecond/1000000.0)
			time.sleep(sleeptime)

if (__name__ == "__main__"):
	import sys
	port = int(sys.argv[1])
	host_ip = sys.argv[2]#"172.17.0.1"

	tmsim = TMSimulator(port,host_ip)
	tmsim.Run()

