import numpy as np
import tables
from tables import IsDescription,open_file,UInt64Col,Float64Col,Float32Col
import struct

class SSReadout(object):
    """
    A class representing a slow signal readout
    """

    def __init__(self, timestamp=0, readout_number = 0, data=None, timestamps=None):
                
        self.readout_number = readout_number
        self.readout_timestamp = timestamp
        self.data =  np.full((32,64),np.nan) if data is None else data 

        #store also the time stamps for the individual readings 
        #two per TM (primary and aux)
        self.timestamps =  np.zeros((32,2),dtype=np.uint64) if timestamps is None else timestamps
        
    def pack(self):
        '''
            Convinience method to pack the readout into a bytestream

            The readout is packed using the folowing format:
                8       bytes encoding the readout number (uint64)
                8       bytes encoding the readout timestamp (uint64)
                2048x8  bytes encoding the 2D readout data using 'C' order (float64)
                64x8    bytes encoding two timetamps for each module in a 2D array using 'C' order (uint64)
        
            returns bytearray
        '''
        d_stream = bytearray(struct.pack('2Q',
                            self.readout_number,
                            self.readout_timestamp))

        d_stream.extend(self.data.tobytes())
        d_stream.extend(self.timestamps.tobytes())
        return d_stream


    def unpack(self,byte_stream):
        '''
        Unpack a bytestream into an readout
        '''
        self.readout_number,self.readout_timestamp = struct.unpack_from('2Q',byte_stream,0)
        self.data = np.frombuffer(byte_stream[8*2:8*(2+2048)],dtype=np.float64).reshape(32,64)
        self.timestamps = np.frombuffer(byte_stream[8*(2+2048):8*(2+2048+64)],dtype=np.uint64).reshape(32,2)

    def __repr__(self):
        return "ssdaq.SSReadout({},\n{},\n{},\n{})".format(self.readout_timestamp,
                                                    self.readout_number,
                                                    repr(self.data),
                                                    repr(self.timestamps))
    def __str__(self):
        return "SSReadout:\n    Readout number: {}\n    Timestamp:    {}\n    data: {}".format(self.readout_number,self.readout_timestamp,str(self.data))
    
class SSReadoutTableDs(IsDescription):

    readout_number = UInt64Col()
    ro_time      = UInt64Col()
    data         = Float32Col((32,64))
    time_stamps  = UInt64Col((32,2))
    
class SSDataWriter(object):
    """A writer for Slow Signal data"""
    def __init__(self,filename, attrs = {},filters = None):
        
        self.filename = filename
        filters = filters if filters != None else tables.Filters(complevel=9, 
                                                                complib='bzip2',#gives us 5 times the speed for the same compression as zlib 
                                                                fletcher32=True)
        self.file = tables.open_file(self.filename, 
                                     mode="w", 
                                     title="CHEC-S Slow signal monitor data",
                                     filters=filters)
        self.group = self.file.create_group(self.file.root, 'SlowSignal', 'Slow signal data')
        self.table = self.file.create_table(self.group, 'readout', SSReadoutTableDs, "Slow signal readout")
        self.ro_row = self.table.row
        self.readout_counter = 0
        for k,v in attrs.items():
            self.table.attrs[k] = v
        self.table.attrs['ssdata_version'] = 1
        
    def write_readout(self, ro):

        self.ro_row['readout_number'] = ro.readout_number
        self.ro_row['ro_time'] = ro.readout_timestamp
        self.ro_row['data'] = np.asarray(ro.data,dtype=np.float32)
        self.ro_row['time_stamps'] = ro.timestamps
        self.ro_row.append()
        self.table.flush()
        self.readout_counter += 1

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
        self.readversions = {0:self.read0,1:self.read1}
        self.attrs = self.file.root.SlowSignal.readout.attrs
        if('ssdata_version' not in self.attrs):
            self.read = self.read0
        else:
            self.read = self.readversions[self.attrs.ssdata_version]
    
    def read0(self,start=None,stop=None,step=None):
        for r in self.file.root.SlowSignal.readout.iterrows(start,stop,step):
            self.raw_readout[:] = r['data']
            self.readout_number = r['event_number']
            self.readout_time = r['ev_time']
            self.readout_timestamps = r['time_stamps']
            #we skip the event_number col since it was never used (put to 0) even with the old format
            yield self.raw_readout
    
    def read1(self,start=None,stop=None,step=None):
        for r in self.file.root.SlowSignal.readout.iterrows(start,stop,step):
            self.raw_readout[:] = r['data']
            self.readout_number = r['readout_number']
            self.readout_time = r['ro_time']
            self.readout_timestamps = r['time_stamps']
            yield self.raw_readout
              
    @property
    def n_readouts(self):
        return self.file.root.SlowSignal.readout.nrows
    
    def __repr__(self):
        return repr(self.file)
    
    def __str__(self):
        s = 'SSDataReader:\n'
        s+='    Filename:%s\n'%self.filename
        s+='    Title: CHEC-S Slow signal monitor data\n'
        s+='    n_readouts: %d\n'%self.n_readouts
        s+='    ssdata-verion: %d\n'%self.attrs.ssdata_version
        
        return s
    def close_file(self):
        self.file.close()