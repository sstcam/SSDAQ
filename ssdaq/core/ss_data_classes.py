import numpy as np
import tables
from tables import IsDescription,open_file,UInt64Col,Float64Col,Float32Col
import struct

N_TM =32 #Number of target modules in camera
N_TM_PIX = 64 #Number of pixels on a Target Module
N_BYTES_NUM = 8 #Number of bytes to encode numbers (uint and float) in the SSReadout
N_CAM_PIX = N_TM*N_TM_PIX #Number of pixels in the camera

class SSReadout(object):
    """
    A class representing a slow signal readout
    """
    

    def __init__(self, timestamp=0, readout_number = 0, data=None, timestamps=None):
                
        self.readout_number = readout_number
        self.readout_timestamp = timestamp
        self.data =  np.full((N_TM,N_TM_PIX),np.nan) if data is None else data 

        #store also the time stamps for the individual readings 
        #two per TM (primary and aux)
        self.timestamps =  np.zeros((N_TM,2),dtype=np.uint64) if timestamps is None else timestamps
        
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
        self.data = np.frombuffer(byte_stream[N_BYTES_NUM*2 : N_BYTES_NUM*(2+N_CAM_PIX)],
                                    dtype=np.float64).reshape(N_TM, N_TM_PIX)
        self.timestamps = np.frombuffer(byte_stream[N_BYTES_NUM*(2+N_CAM_PIX):N_BYTES_NUM*(2+N_CAM_PIX+N_TM*2)],
                                        dtype=np.uint64).reshape(N_TM,2)

    def __repr__(self):
        return "ssdaq.SSReadout({},\n{},\n{},\n{})".format(self.readout_timestamp,
                                                    self.readout_number,
                                                    repr(self.data),
                                                    repr(self.timestamps))
    def __str__(self):
        return "SSReadout:\n    Readout number: {}\n    Timestamp:    {}\n    data: {}".format(self.readout_number,
                                                                                                self.readout_timestamp,
                                                                                                str(self.data))
    
class SSReadoutTableDs(IsDescription):

    readout_number = UInt64Col()
    ro_time      = UInt64Col()
    data         = Float32Col((N_TM,N_TM_PIX))
    time_stamps  = UInt64Col((N_TM,2))
    
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
        self.ro_row['data'] = np.asarray(ro.data, dtype=np.float32)
        self.ro_row['time_stamps'] = ro.timestamps
        self.ro_row.append()
        self.table.flush()
        self.readout_counter += 1

    def close_file(self):
        self.table.flush()
        self.file.close()

from collections import namedtuple as _nt
 
_SSMappings = _nt('SSMappings','ssl2colrow ssl2asic_ch')
ss_mappings = _SSMappings(np.array([ 9, 12,  2, 15, 13, 11,  3, 17, 27, 18, 29,  4, 28, 25, 31,  1,  6,
       14,  7,  8,  5, 10, 16, 20, 21, 19, 32, 26, 22, 30, 23, 24, 42, 45,
       44, 37, 39, 41, 38, 40, 57, 63, 55, 54, 59, 50, 53, 58, 52, 43, 48,
       47, 34, 35, 46, 49, 36, 33, 64, 62, 60, 51, 56, 61], dtype=np.uint64),
        np.array([29, 23, 21, 22, 30, 27, 24,  0, 25, 31, 20, 18, 28, 26, 17,  3,  2,
       16, 10, 12, 19,  4, 15,  9,  1,  8, 11, 14,  6,  7,  5, 13, 62, 56,
       54, 53, 59, 60, 55, 50, 57, 58, 52, 49, 61, 63, 32, 35, 51, 47, 42,
       46, 33, 34, 45, 48, 44, 36, 41, 43, 40, 38, 39, 37], dtype=np.uint64),
 )


class SSDataReader(object):
    """A reader for Slow Signal data"""
    def __init__(self, filename, mapping='ssl2asic_ch'):
        self.filename = filename
        self.file = tables.open_file(self.filename, mode="r")        

        self.raw_readout = np.zeros((N_TM,N_TM_PIX),dtype=np.float32)
        self.readout = np.zeros((N_TM,N_TM_PIX),dtype=np.float32)
        self.readout_number = None
        self.readout_time = None
        self.readout_timestamps = np.zeros((N_TM,2), dtype=np.uint64)
        
        self._readversions = {0:self._read0,1:self._read1}
        self.attrs = self.file.root.SlowSignal.readout.attrs
        
        try:
            self.map = ss_mappings.__getattribute__(mapping)
        except:
            raise ValueError('No mapping found with name %s'%mapping)
        
        if('ssdata_version' not in self.attrs):
            self.read = self._read0
        else:
            self.read = self._readversions[self.attrs.ssdata_version]
    
    def _read0(self,start=None,stop=None,step=None):
        for r in self.file.root.SlowSignal.readout.iterrows(start,stop,step):
            self.raw_readout[:] = r['data']
            self.readout[:] = r['data'][:,self.map]
            self.readout_number = r['event_number']
            self.readout_time = r['ev_time']
            self.readout_timestamps = r['time_stamps']
            #we skip the event_number col since it was never used (put to 0) even with the old format
            yield self.readout
    
    def _read1(self,start=None,stop=None,step=None):
        for r in self.file.root.SlowSignal.readout.iterrows(start,stop,step):
            self.raw_readout[:] = r['data']
            self.readout[:] = r['data'][:,self.map]
            self.readout_number = r['readout_number']
            self.readout_time = r['ro_time']
            self.readout_timestamps = r['time_stamps']
            yield self.readout
              
    @property
    def n_readouts(self):
        return self.file.root.SlowSignal.readout.nrows

    def load_all_data_tm(self,tm, calib=None, mapping=None):
        '''Loads all rows of data for a particular target moduel into memory
            
            Args:
                tm (int):   The slot number of the target module 

            Kwargs:
                calib (arraylike): an array with calibration coefficient that should be applied to the data
                mapping (str or arraylike): a string to select a mapping  or an array with the mapping
                                            ['ssl2colrow','ssl2asic_ch','raw']  
        '''
        from collections import namedtuple
        if calib is None:
            calib = 1.0 
        if(mapping is None):
            map = self.map
        elif(isinstance(mapping,str)):
            if(mapping == 'raw'):
                map = np.arange(N_TM_PIX)
            else:
                try:
                    map = ss_mappings.__getattribute__(mapping)
                except:
                    raise ValueError('No mapping found with name %s'%mapping)        
        else:
            map = mapping

        amps = np.zeros((self.n_readouts,N_TM_PIX)) 
        time = np.zeros(self.n_readouts)
        iro = np.zeros(self.n_readouts,dtype=np.uint64)

        for i, r in enumerate(self.read()):
            amps[i,:] = self.raw_readout[tm,:]*calib
            time[i] = self.readout_time
            iro[i] = self.readout_number
        

                
        amps = amps[:,map]

        ssdata = namedtuple('ssdata','iro amps time tm')
        return ssdata(iro,amps,time,tm)

    
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