from ssdaq.core import SSEventListener
from threading import Thread
import numpy as np
import tables
from tables import IsDescription,open_file,UInt64Col,Float64Col,Float32Col


class SSEventTableDs(IsDescription):
    event_number = UInt64Col()
    runt_number = UInt64Col()
    ev_time = UInt64Col()
    data = Float32Col((32,64))
    time_stamps = UInt64Col((32,2))

class EventFileWriter(Thread):
    
    def __init__(self, filename):
        Thread.__init__(self)
        self.filename = filename
        self.event_listener = SSEventListener.SSEventListener()
        self.file = open_file(filename, mode="w", title="CHEC-S Slow signal monitor data")
        self.group = self.file.create_group("/", 'SlowSignal', 'Slow signal data')
        self.table = self.file.create_table(self.group, 'readout', SSEventTableDs, "Slow signal readout")
        self.running = False
        self.event_counter = 0
    
    def run(self):
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
        self.event_listener.CloseThread()
        self.file.close()
        print('EventFileWriter has written %d events to file'%self.event_counter)





