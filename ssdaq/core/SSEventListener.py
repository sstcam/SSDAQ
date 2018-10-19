from ssdaq.core import SSEventBuilder 

from threading import Thread
import zmq
from queue import Queue

class SSEventListener(Thread):
    def __init__(self, port = '5555'):
        Thread.__init__(self)
        
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.SUB)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        self.sock.connect("tcp://127.0.0.101:"+port)
        self.running = False
        self.event_buffer = Queue()
    
    def run(self):
        self.running = True

        while(self.running):
            data = self.sock.recv()
            event = SSEventBuilder.SSEvent()
            event.unpack(data)
            self.event_buffer.put(event)