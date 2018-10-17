from threading import Thread
import os
import numpy as np
import struct
import zmq

from .SSEventBuilder import SSEvent

class SSEventDataPublisher(Thread):
	def __init__(self,port,event_queue):
		Thread.__init__(self)
		self.event_queue = event_queue
		self.context = zmq.Context()
		self.sock = self.context.socket(zmq.PUB)
		self.sock.bind('tcp://*:'+str(port))
		self.running = False

	def run(self):
		self.running = True
		self.setName('SSEventDataPublisher')
		while(self.running):
			while(not self.event_queue.empty()):
				event = self.event_queue.get()
				self.sock.send(event.pack())
