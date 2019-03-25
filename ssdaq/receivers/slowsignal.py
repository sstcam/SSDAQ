from ssdaq import SSReadout

from ssdaq import SSDataWriter
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
    def __init__(self,ip:str,port:int,logger:logging.Logger=None):
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


class SSFileWriter(Thread):
    """
    A data file writer for slow signal data.

    This class uses a instance of a SSReadoutListener to receive readouts and
    an instance of SSDataWriter to write an HDF5 file to disk.
    """
    def __init__(self, file_prefix:str,ip:str,port:int, folder:str='',file_enumerator:str=None,):
        from ssdaq import sslogger
        import logging
        Thread.__init__(self)
        self.file_enumerator =file_enumerator
        self.folder = folder
        self.file_prefix = file_prefix
        self.log = sslogger.getChild('SSFileWriter')
        self._readout_listener = SSReadoutListener(logger=self.log.getChild('Listener'),ip=ip,port=port)
        self.running = False
        self.readout_counter = 0
        self.file_counter = 1
        self._open_file()

    def _open_file(self):
        import os
        from datetime import datetime
        self.file_readout_counter = 0
        if(self.file_enumerator == 'date'):
            suffix = datetime.utcnow().strftime("%Y-%m-%d_%H.%M")
        elif(self.file_enumerator == 'order'):
            suffix = '%0.3d'%self.file_counter
        else:
            suffix = ''


        self.filename = os.path.join(self.folder,self.file_prefix+suffix+'.hdf5')
        self._writer = SSDataWriter(self.filename)
        self.log.info('Opened new file, will write events to file: %s'%self.filename)

    def _close_file(self):
        import os
        from ssdaq.utils.file_size import convert_size
        self.log.info('Closing file %s'%self.filename)
        self._writer.close_file()
        self.log.info('SSFileWriter has written %d events in %s bytes to file %s'%(self._writer.readout_counter,
                                                                                      convert_size(os.stat(self.filename).st_size),
                                                                                      self.filename))
    def close(self):
        self.running = False
        self._readout_listener.close()
        self.join()

    def run(self):
        self.log.info('Starting writer thread')
        self._readout_listener.start()
        self.running = True
        while(self.running):
            readout = self._readout_listener.get_readout()
            if(readout == None):
                continue
            #Start a new file if we get
            #an readout with readout number 1
            if(readout.iro==1 and self.readout_counter>0):
                self._close_file()
                self.file_counter += 1
                self._open_file()

            self._writer.write_readout(readout)
            self.readout_counter +=1

        self.log.info('Stopping listener thread')
        self._readout_listener.close()
        self._close_file()
        self.log.info('SSFileWriter has written a'
                      ' total of %d events to %d file(s)'%(self.readout_counter,
                                                            self.file_counter))





