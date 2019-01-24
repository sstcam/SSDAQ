import numpy as np
import tables
from tables import IsDescription,open_file,UInt64Col,Float64Col,Float32Col
import struct

class SSEvent(object):
    """
    A class representing a slow signal event
    """

    def __init__(self, timestamp=0, event_number = 0,data=None,timestamps=None):
                
        self.event_number = event_number
        self.event_timestamp = timestamp
        self.data = np.empty((32,64)) if data == None else data
        self.data[:] = np.nan
        #store also the time stamps for the individual readings 
        #two per TM (primary and aux)
        self.timestamps = np.zeros((32,2),dtype=np.uint64) if timestamps == None else timestamps
        
    def pack(self):
        '''
        Convinience method to pack the event into a bytestream
        '''
        d_stream = bytearray(struct.pack('2Q',
                            self.event_number,
                            self.event_timestamp))

        d_stream.extend(self.data.tobytes())
        d_stream.extend(self.timestamps.tobytes())
        return d_stream


    def unpack(self,byte_stream):
        '''
        Unpack a bytestream into an event
        '''
        self.event_number,self.event_timestamp = struct.unpack_from('2Q',byte_stream,0)
        self.data = np.frombuffer(byte_stream[8*2:8*(2+2048)],dtype=np.float64).reshape(32,64)
        self.timestamps = np.frombuffer(byte_stream[8*(2+2048):8*(2+2048+64)],dtype=np.uint64).reshape(32,2)

    def __repr__(self):
        return "ssdaq.SSEvent({},\n{},\n{},\n{})".format(self.event_timestamp,
                                                    self.event_number,
                                                    repr(self.data),
                                                    repr(self.timestamps))
    def __str__(self):
        return "SSEvent:\n    Event number: {}\n    Timestamp:    {}\n    data: {}".format(self.event_number,self.event_timestamp,str(self.data))

class SSEventTableDs(IsDescription):

    event_number = UInt64Col()
    ev_time      = UInt64Col()
    data         = Float32Col((32,64))
    time_stamps  = UInt64Col((32,2))

class SSDataWriter(object):
    """A writer for Slow Signal data"""
    def __init__(self,filename):
        self.filename = filename
        self.file = tables.open_file(self.filename, mode="w", title="CHEC-S Slow signal monitor data")
        self.group = self.file.create_group(self.file.root, 'SlowSignal', 'Slow signal data')
        self.table = self.file.create_table(self.group, 'readout', SSEventTableDs, "Slow signal readout")
        self.ev_row = self.table.row
        self.event_counter = 0

    def write_readout(self, ev):

        self.ev_row['event_number'] = ev.event_number
        self.ev_row['ev_time'] = ev.event_timestamp
        self.ev_row['data'] = np.asarray(ev.data,dtype=np.float32)
        self.ev_row['time_stamps'] = ev.timestamps
        self.ev_row.append()
        self.table.flush()
        self.event_counter += 1

    def close_file(self):
        self.table.flush()
        self.file.close()


class SSDataReader(object):
    """A reader for Slow Signal data"""
    def __init__(self,filename):
        self.filename = filename
        self.file = tables.open_file(self.filename, mode="r")        

        self.raw_readout = np.zeros((32,64),dtype=np.float32)
        self.readout_number = None
        self.readout_time = None
        self.readout_timestamps = np.zeros((32,2),dtype=np.uint64)

    def read(self,start=None,stop=None,step=None):
        for r in self.file.root.SlowSignal.readout.iterrows(start,stop,step):
            self.raw_readout[:] = r['data']
            self.readout_number = r['event_number']
            self.readout_time = r['ev_time']
            self.readout_timestamps = r['time_stamps']
            yield self.raw_readout
              
    @property
    def n_readouts(self):
        return self.file.root.SlowSignal.readout.nrows
    
    def __repr__(self):
        return repr(self.file)
