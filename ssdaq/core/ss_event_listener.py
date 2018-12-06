from ssdaq import SSEvent

from threading import Thread
import zmq
from queue import Queue
import logging

class SSEventListener(Thread):
    ''' A convinience class to subscribe to a published SS event data stream. 
        Events are retrived by the `get_event()` method once the listener has been started by the 
        `start()` method

        Args:
            ip (str):   The ip address where the events are published (can be local or remote) 
            port (int): The port number at which the events are published
        Kwargs:
            logger:     Optionally provide a logger instance 
    '''
    id_counter = 0
    def __init__(self,ip,port,logger=None):
        Thread.__init__(self)
        SSEventListener.id_counter += 1
        if(logger == None):
            self.log=logging.getLogger('ssdaq.SSEventListener%d'%SSEventListener.id_counter) 
        else:
            self.log=logger

        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.SUB)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        con_str = "tcp://%s:%s"%(ip,port)
        if('0.0.0.0' == ip):
            self.sock.bind(con_str)
        else:
            self.sock.connect(con_str)
        self.log.info('Connected to : %s'%con_str)
        self.running = False
        self._event_buffer = Queue()
        
        self.id_counter = SSEventListener.id_counter
        self.inproc_sock_name = "SSEventListener%d"%(self.id_counter) 
        self.close_sock = self.context.socket(zmq.PAIR)
        self.close_sock.bind("inproc://"+self.inproc_sock_name)
        

    def close(self):
        ''' Closes listener thread and empties the event buffer to unblock the
            the get_event method  
        '''

        if(self.running):
            self.log.debug('Sending close message to listener thread')
            self.close_sock.send(b"close")
        self.log.debug('Emptying event buffer')
        #Empty the buffer after closing the recv thread
        while(not self._event_buffer.empty()):
            self._event_buffer.get()
            self._event_buffer.task_done()
        self._event_buffer.join()

    def get_event(self,**kwargs):
        ''' Returns an SSEvent instance from the published event stream.
            By default a blocking call. See python Queue docs.

            Kwargs:
                Se Queue docs

        '''
        event = self._event_buffer.get(**kwargs)
        self._event_buffer.task_done()       
        return event

    def run(self):
        ''' This is the main method of the listener
        '''
        self.log.info('Starting listener')
        recv_close = self.context.socket(zmq.PAIR)
        con_str = "inproc://"+self.inproc_sock_name
        recv_close.connect(con_str)
        self.running = True
        self.log.debug('Connecting close socket to %s'%con_str)
        poller = zmq.Poller()
        poller.register(self.sock,zmq.POLLIN)
        poller.register(recv_close,zmq.POLLIN)

        while(self.running):
            
            socks= dict(poller.poll())
            
            if(self.sock in socks):
                data = self.sock.recv()
                event = SSEvent()
                event.unpack(data)
                self._event_buffer.put(event)
            else:
                self.log.info('Stopping')
                event = SSEvent()
                self._event_buffer.put(None)
                break
        self.running = False