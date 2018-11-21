from ssdaq import SSEventListener
from threading import Thread
import numpy as np
import tables
from tables import IsDescription,open_file,UInt64Col,Float64Col,Float32Col
import logging

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
    def __init__(self, filename):
        from ssdaq import sslogger
        Thread.__init__(self)
        self.filename = filename
        self.log = sslogger.getChild('EventFileWriter')
        self.event_listener = SSEventListener.SSEventListener(logger=self.log.getChild('EventListener'))
        self.file = open_file(filename, mode="w", title="CHEC-S Slow signal monitor data")
        self.group = self.file.create_group("/", 'SlowSignal', 'Slow signal data')
        self.table = self.file.create_table(self.group, 'readout', SSEventTableDs, "Slow signal readout")
        self.running = False
        self.event_counter = 0
        self.log.info('Initialized, will write events to file: %s'%self.filename)
    
    def run(self):
        self.log.info('Starting writer thread')
        self.event_listener.start()
        self.running = True
        ev_row = self.table.row  
        while(self.running):
            event = self.event_listener.GetEvent()
            ev_row['event_number'] = event.event_number
            ev_row['ev_time'] = event.event_timestamp
            ev_row['data'] = np.asarray(event.data,dtype=np.float32)
            ev_row['time_stamps'] = event.timestamps
            ev_row.append()
            self.table.flush()
            self.event_counter +=1
        self.log.info('Stopping listener thread')
        self.event_listener.CloseThread()
        self.log.info('Closing file %s'%self.filename)
        self.file.close()
        self.log.info('EventFileWriter has written %d events to file %s'%(self.event_counter,self.filename))





