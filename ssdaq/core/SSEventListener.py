from ssdaq.core import SSEventBuilder 

from threading import Thread
import zmq
from queue import Queue
import logging

class SSEventListener(Thread):
    id_counter = 0
    def __init__(self, port = '5555',logger=None):
        Thread.__init__(self)
        
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.SUB)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        self.sock.connect("tcp://127.0.0.101:"+port)
        self.running = False
        self._event_buffer = Queue()
        SSEventListener.id_counter += 1
        self.id_counter = SSEventListener.id_counter
        self.inproc_sock_name = "SSEventListener%d"%(self.id_counter) 
        self.close_sock = self.context.socket(zmq.PAIR)
        self.close_sock.bind("inproc://"+self.inproc_sock_name)
        if(logger == None):
            self.log=logging.getLogger('ssdaq.SSEventListener')
        else:
            self.log=logger
    def CloseThread(self):

        if(self.running):
            self.log.debug('Sending close message to listener thread')
            self.close_sock.send(b"close")
        self.log.debug('Emptying event buffer')
        #Empty the buffer after closing the recv thread
        while(not self._event_buffer.empty()):
            self._event_buffer.get()
            self._event_buffer.task_done()
        self._event_buffer.join()

    def GetEvent(self,**kwargs):
        event = self._event_buffer.get(**kwargs)
        self._event_buffer.task_done()       
        return event

    def run(self):
        self.log.info('Starting listener')
        recv_close = self.context.socket(zmq.PAIR)
        con_str = "inproc://"+self.inproc_sock_name
        recv_close.connect(con_str)
        self.running = True
        self.log.info('Connecting to %s'%con_str)
        poller = zmq.Poller()
        poller.register(self.sock,zmq.POLLIN)
        poller.register(recv_close,zmq.POLLIN)

        while(self.running):
            
            socks= dict(poller.poll())
            
            if(self.sock in socks):
                data = self.sock.recv()
                event = SSEventBuilder.SSEvent()
                event.unpack(data)
                self._event_buffer.put(event)
            else:
                self.log.info('Stopping')
                break
        self.running = False