from ssdaq import SSReadout

from threading import Thread
import zmq
from queue import Queue
import logging

class SSReadoutListener(Thread):
    ''' A convinience class to subscribe to a published SS readout data stream.
        readouts are retrived by the `get_readout()` method once the listener has been started by the
        `start()` method

        Args:
            ip (str):   The ip address where the readouts are published (can be local or remote)
            port (int): The port number at which the readouts are published
        Kwargs:
            logger:     Optionally provide a logger instance
    '''
    id_counter = 0
    def __init__(self,ip,port,logger=None):
        Thread.__init__(self)
        SSReadoutListener.id_counter += 1
        if(logger == None):
            self.log=logging.getLogger('ssdaq.SSReadoutListener%d'%SSReadoutListener.id_counter)
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
        self._readout_buffer = Queue()

        self.id_counter = SSReadoutListener.id_counter
        self.inproc_sock_name = "SSReadoutListener%d"%(self.id_counter)
        self.close_sock = self.context.socket(zmq.PAIR)
        self.close_sock.bind("inproc://"+self.inproc_sock_name)


    def close(self):
        ''' Closes listener thread and empties the readout buffer to unblock the
            the get_readout method
        '''

        if(self.running):
            self.log.debug('Sending close message to listener thread')
            self.close_sock.send(b"close")
        self.log.debug('Emptying readout buffer')
        #Empty the buffer after closing the recv thread
        while(not self._readout_buffer.empty()):
            self._readout_buffer.get()
            self._readout_buffer.task_done()
        self._readout_buffer.join()

    def get_readout(self,**kwargs):
        ''' Returns an SSReadout instance from the published readout stream.
            By default a blocking call. See python Queue docs.

            Kwargs:
                See queue.Queue docs

        '''
        readout = self._readout_buffer.get(**kwargs)
        self._readout_buffer.task_done()
        return readout

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
                readout = SSReadout()
                readout.unpack(data)
                self._readout_buffer.put(readout)
            else:
                self.log.info('Stopping')
                readout = SSReadout()
                self._readout_buffer.put(None)
                break
        self.running = False