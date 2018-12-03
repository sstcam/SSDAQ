from ssdaq import SSEventListener
from threading import Thread
import numpy as np
import tables
from tables import IsDescription,open_file,UInt64Col,Float64Col,Float32Col


class SSEventTableDs(IsDescription):
    event_number = UInt64Col()
    runt_number  = UInt64Col()
    ev_time      = UInt64Col()
    data         = Float32Col((32,64))
    time_stamps  = UInt64Col((32,2))

class EventFileWriter(Thread):
    """
    An event data file writer for slow signal data.

    This class uses a instance of an SSEventListener to receive events and
    implements a HDF5 table writer that writes the events to disk.
    """
    def __init__(self, file_prefix, folder='',file_enumerator=None,**kwargs):
        from ssdaq import sslogger
        import logging
        Thread.__init__(self)
        self.file_enumerator =file_enumerator
        self.folder = folder
        self.file_prefix = file_prefix
        self.log = sslogger.getChild('EventFileWriter')
        self.event_listener = SSEventListener(logger=self.log.getChild('EventListener'),**kwargs)
        self.running = False
        self.event_counter = 0
        self.file_event_counter = 0
        self.file_counter = 1
        self._open_file()
    
    def _open_file(self):
        import os
        from datetime import datetime
        self.file_event_counter = 0
        if(self.file_enumerator == 'date'):
            suffix = datetime.utcnow().strftime("%Y-%m-%d.%H:%M")
        elif(self.file_enumerator == 'order'):
            suffix = '%0.3d'%self.file_counter
        else:
            suffix = ''

        self.filename = os.path.join(self.folder,self.file_prefix+suffix+'.hdf5') 
        self.file = open_file(self.filename, mode="w", title="CHEC-S Slow signal monitor data")
        self.group = self.file.create_group("/", 'SlowSignal', 'Slow signal data')
        self.table = self.file.create_table(self.group, 'readout', SSEventTableDs, "Slow signal readout")
        self.log.info('Opened new file, will write events to file: %s'%self.filename)

    def _close_file(self):
        import os
        from ssdaq.utils.file_size import convert_size
        self.table.flush()
        self.log.info('Closing file %s'%self.filename)
        self.file.close()
        self.log.info('EventFileWriter has written %d events in %s bytes to file %s'%(self.file_event_counter,
                                                                                      convert_size(os.stat(self.filename).st_size),
                                                                                      self.filename))
    def close(self):
        self.running = False
        self.event_listener.CloseThread()
        self.join()

    def run(self):
        self.log.info('Starting writer thread')
        self.event_listener.start()
        self.running = True
        ev_row = self.table.row
        while(self.running):
            event = self.event_listener.GetEvent()
            if(event == None):
                continue
            #Start a new file if we get 
            #an event with event number 1
            if(event.event_number==1):
                self._close_file()
                self.file_counter += 1
                self._open_file()
                ev_row = self.table.row  
            ev_row['event_number'] = event.event_number
            ev_row['ev_time'] = event.event_timestamp
            ev_row['data'] = np.asarray(event.data,dtype=np.float32)
            ev_row['time_stamps'] = event.timestamps
            ev_row.append()
            self.table.flush()
            self.event_counter +=1
            self.file_event_counter +=1

        self.log.info('Stopping listener thread')
        self.event_listener.CloseThread()
        self._close_file()        
        self.log.info('EventFileWriter has written a'
                      ' total of %d events to %d file(s)'%(self.event_counter,
                                                            self.file_counter))





