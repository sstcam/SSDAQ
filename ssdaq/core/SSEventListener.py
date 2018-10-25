from ssdaq.core import SSEventBuilder 

from threading import Thread
import zmq
from queue import Queue

class SSEventListener(Thread):
    id_counter = 0
    def __init__(self, port = '5555'):
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

    def CloseThread(self):
        if(self.running):
            self.close_sock.send(b"close")
        # #Empty the buffer after closing the recv thread
        while(not self._event_buffer.empty()):
            self._event_buffer.get()
            self._event_buffer.task_done()
        self._event_buffer.join()

    def GetEvent(self,**kwargs):
        event = self._event_buffer.get(**kwargs)
        self._event_buffer.task_done()       
        return event

    def run(self):
        print('Starting listener')
        recv_close = self.context.socket(zmq.PAIR)
        recv_close.connect("inproc://"+self.inproc_sock_name)
        self.running = True

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
                print('Stopping')
                break
        self.running = False