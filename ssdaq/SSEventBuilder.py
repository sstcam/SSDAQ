from queue import Queue
from threading import Thread
import os
import numpy as np
import struct

class DataStream(bytearray):
    def append(self, v, fmt='>B'):
        self.extend(struct.pack(fmt, v))

class SSEvent(object):
	"""
	A class representing a slow signal event
	"""

	def __init__(self,timestamp):
		self.event_timestamp = timestamp
		self.data = np.empty((32,64))
		self.data[:] = np.nan
		self.timestamps = np.zeros((32,2),dtype=np.uint64)
	
	def pack(self):
		d_stream = DataStream()
		d_stream.append(self.event_timestamp,'Q')
		for v in self.data.ravel():
				d_stream.append(v,'d')
		for v in self.timestamps.ravel():
				d_stream.append(v,'Q')
		return d_stream
	def unpack(byte_stream):
		self.event_timestamp = struct.unpack_from('Q',byte_stream,0)[0]
		self.data = np.asarray(struct.unpack_from('2048d',byte_stream,8)).reshape(32,64)
		self.timestamps = np.asarray(struct.unpack_from('64Q',byte_stream,8+8*2048)).reshape(32,2)


READOUT_LENGTH = 64*2+2*8
class SSEventBuilder(Thread):
	""" 
	Slow signal event builder. Constructs 
	slow signal events from data packets recieved from 
	Target Modules.
	"""
	def __init__(self):
		Thread.__init__(self)
		self.data_queue = Queue()
		self.event_queue = Queue()

		self.inter_data = {}
		self.next_time_stamps = np.zeros(32,dtype = np.uint64)
		#assume we always have 32 modules
		for i in range(32):
			self.inter_data[i] = []
		

		self.running = False
		self.event_tw = int(5e6)

	def _build_event(self):
		#updating latest timestamps for a potential event
		for k,v in self.inter_data.items():
			if(len(v)!=0):
				self.next_time_stamps[k] = v[0][0]
			else:
				self.next_time_stamps[k] = 0
		
		#Data from one TM is enough for an event
		if(np.sum(self.next_time_stamps>0)>0):

			#find all data that is within the event tw of the
			#earliest time stamp
			earliest_ts = np.min(self.next_time_stamps[self.next_time_stamps>0])
			m = ((self.next_time_stamps-earliest_ts) < self.event_tw) & ((self.next_time_stamps-earliest_ts)>=0)
			
			#construct event
			event = SSEvent(int(np.mean(self.next_time_stamps[m])))
			for k in np.where(m)[0]:

				tmp_data = self.inter_data[k].pop(0)[1]
				tmp_array = np.empty(64,dtype=np.uint64)
				tmp_array[:32] = tmp_data[1:33]
				tmp_array[32:] = tmp_data[34:]
				#converting counts to mV
				m = tmp_array < 0x8000
				tmp_array[m] += 0x8000
				tmp_array[~m] = tmp_array[~m]&0x7FFF
				event.data[k] = tmp_array* 0.03815*2.

				event.timestamps[k][0]=tmp_data[0]
				event.timestamps[k][1]=tmp_data[33]
				

			self.event_queue.put(event)

	def run(self):
		self.running = True
		self.setName('SSEventBuilder')
		while(self.running):
			
			while(not self.data_queue.empty()):
				data = self.data_queue.get()
				nreadouts = int(len(data[1])/(READOUT_LENGTH))
				if(len(data[1])%(READOUT_LENGTH) != 0):
					print("Warning: Got unsuported packet size")
				
				print("Got data from %s"%(str(data[0])))
				module_nr = int(data[0][-2:])
				print("Module number %d "%(module_nr))
				# self.inter_data[module_nr].put()
				for i in range(nreadouts):
					unpacked_data = struct.unpack_from('Q32H'+'Q32H',data[1],i*(64*2+2*8))
					self.inter_data[module_nr].append((unpacked_data[0],unpacked_data))
					# print('Readout ',i, struct.unpack_from('Q32H'+'Q32H',data[1],i*(64*2+2*8)))

			self._build_event()

			# print('Buffer lengths %d %d'%(self.data_queue.qsize(),self.event_queue.qsize()))







