from ssdaq import SSReadoutListener, SSDataWriter
from threading import Thread

class SSFileWriter(Thread):
    """
    A data file writer for slow signal data.

    This class uses a instance of a SSReadoutListener to receive readouts and
    an instance of SSDataWriter to write a HDF5 file to disk.
    """
    def __init__(self, file_prefix,ip,port, folder='',file_enumerator=None,**kwargs):
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
            suffix = datetime.utcnow().strftime("%Y-%m-%d.%H:%M")
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





