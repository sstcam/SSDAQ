import struct
import binascii

_chunk_header = struct.Struct("2I")

###Raw object IO classes#####


class RawObjectWriterBase:
    """ Acts as a file object for writing chunks of serialized data
        to file. Prepends each chunk with:
        chunk length in bytes (4 bytes)
        and a crc32 hash      (4 bytes)
    """

    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, "wb")
        self.data_counter = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def write(self, data: bytes):
        """
        """
        self.file.write(_chunk_header.pack(len(data), binascii.crc32(data)))
        self.file.write(data)
        self.data_counter += 1

    def close(self):
        self.file.close()


class RawObjectReaderBase:
    """
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(self.filename, "rb")
        self._scan_file()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def _scan_file(self):
        offset = 0
        fh = self.file
        self.n_entries = 0
        self.fpos = []
        fp = 0
        while True:
            fh.seek(fp)
            rd = fh.read(_chunk_header.size)
            if rd == b"":
                break
            self.fpos.append(fp)
            offset, crc = _chunk_header.unpack(rd)
            self.n_entries += 1
            fp = fh.tell() + offset
        self.file.seek(0)

    def read(self) -> bytes:
        sized = self.file.read(_chunk_header.size)
        if sized == b"":
            return None
        size, crc = _chunk_header.unpack(sized)
        return self.file.read(size)

    def close(self):
        self.file.close()


###End of Raw object IO classes#####

### Specialization to different protobuf protocols#####
from ssdaq.core.logging import log_pb2


class LogWriter(RawObjectWriterBase):
    def write(self, log: log_pb2.LogData):
        super().write(log.SerializeToString())


class LogReader(RawObjectReaderBase):
    def read(self):
        log = log_pb2.LogData()
        data = super().read()
        log.ParseFromString(data)
        return log


from ssdaq.core.timestamps import CDTS_pb2


class TimestampWriter(RawObjectWriterBase):
    def write(self, timestamp):
        super().write(timestamp.SerializeToString())


class TimestampReader(RawObjectReaderBase):
    def read(self):
        timestamp = CDTS_pb2.TriggerMessage()
        data = super().read()
        timestamp.ParseFromString(data)
        return timestamp


from ssdaq.core.triggers import data


class TriggerWriter(RawObjectWriterBase):
    def write(self, trigg):
        super().write(
            data.NominalTriggerDataEncode.pack(
                trigg.TACK,
                trigg.trigg,
                trigg.uc_ev,
                trigg.uc_pps,
                trigg.uc_clock,
                trigg.type,
            )
        )


class TriggerReader(RawObjectReaderBase):
    def read(self):
        return data.TriggerPacketData.unpack(super().read())
