from datetime import datetime
import numpy as np
import struct
from collections import namedtuple as _nt
import sys

N_TM = 32  # Number of target modules in camera
N_TM_PIX = 64  # Number of pixels on a Target Module
N_BYTES_NUM = 8  # Number of bytes to encode numbers (uint and float) in the SSReadout
N_CAM_PIX = N_TM * N_TM_PIX  # Number of pixels in the camera

# fmt: off
_SSMappings = _nt("SSMappings", "ssl2colrow ssl2asic_ch")
ss_mappings = _SSMappings(
    np.array(
        [8, 1, 5, 6, 41, 43, 51, 47, 11, 14, 13, 7, 44, 36, 42, 46, 12, 2, 4, 15, 38,
         37, 33, 45, 10, 16, 9, 19, 40, 39, 34, 48, 26, 28, 20, 31, 56, 54, 35, 63,
         17, 3, 18, 25, 62, 53, 32, 61, 27, 30, 21, 22, 58, 52, 59, 55, 24, 0, 29,
         23, 49, 57, 50, 60,],dtype=np.uint64),

    np.array(
        [29, 23, 21, 22, 30, 27, 24, 0, 25, 31, 20, 18, 28, 26, 17, 3, 2, 16, 10, 12,
         19, 4, 15, 9, 1, 8, 11, 14, 6, 7, 5, 13, 62, 56, 54, 53, 59, 60, 55, 50, 57,
         58, 52, 49, 61, 63, 32, 35, 51, 47, 42, 46, 33, 34, 45, 48, 44, 36, 41, 43,
         40, 38, 39, 37], dtype=np.uint64,
    ),
)
# fmt: on


class SSReadout(object):
    """
    A class representing a full camera slow signal readout
    """

    def __init__(
        self,
        timestamp: int = 0,
        readout_number: int = 0,
        cpu_t_s: int = 0,
        cpu_t_ns: int = 0,
        data: np.array = None,
    ):

        self.iro = readout_number
        self.time = timestamp
        self.cpu_t_s = cpu_t_s
        self.cpu_t_ns = cpu_t_ns
        self.data = np.full((N_TM, N_TM_PIX), np.nan,dtype=np.dtype("<f8")) if data is None else data
        #Keeping the data in little endiann (assumed to be the mostly used endiann format)
        if sys.byteorder != 'little' and self.data.dtype.byteorder !='<':
            self.data = self.data.byteswap()

    @classmethod
    def from_bytes(cls, data):
        inst = cls()
        inst.unpack(data)
        return inst

    def pack(self):
        """
            Convinience method to pack the readout into a bytestream

            The readout is packed using the folowing format:
                8       bytes encoding the readout number (uint64)
                8       bytes encoding the readout timestamp (TACK) (uint64)
                8       bytes encoding the readout cpu timestamp seconds (uint64)
                8       bytes encoding the readout cpu timestamp nanoseconds (uint64)
                2048x8  bytes encoding the 2D readout data using 'C' order (float64)

            returns bytearray
        """
        d_stream = bytearray(
            struct.pack("<4Q", self.iro, self.time, self.cpu_t_s, self.cpu_t_ns)
        )

        d_stream.extend(self.data.tobytes())
        return d_stream

    def unpack(self, byte_stream):
        """
        Unpack a bytestream into an readout
        """
        self.iro, self.time, self.cpu_t_s, self.cpu_t_ns = struct.unpack_from(
            "<4Q", byte_stream, 0
        )
        self.data = np.frombuffer(
            byte_stream[N_BYTES_NUM * 4 : N_BYTES_NUM * (4 + N_CAM_PIX)],
            dtype=np.dtype("<f8"),
        ).reshape(N_TM, N_TM_PIX)

    def __repr__(self):
        return "ssdaq.SSReadout({},\n{},\n{},\n{},\n{})".format(
            self.time, self.iro, self.cpu_t_s, self.cpu_t_ns, repr(self.data)
        )

    def __str__(self):
        return "SSReadout:\n    Readout number: {}\n    Timestamp:    {}\n    CPU Timestamp:    {}\n    data: {}".format(
            self.iro, self.time, self.cpu_t, str(self.data)
        )

    def _get_asic_mapped(self):
        return self.data[:, ss_mappings.ssl2asic_ch]

    def _get_colrow_mapped(self):
        return self.data[:, ss_mappings.ssl2colrow]

    @property
    def cpu_t(self):
        return float(self.cpu_t_s) + self.cpu_t_ns * 1e-9

    asic_mapped_data = property(lambda self: self._get_asic_mapped())
    colrow_mapped_data = property(lambda self: self._get_colrow_mapped())
