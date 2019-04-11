import struct
import binascii

header = struct.Struct("2I")

###Raw object IO


class RawObjectWriterBase:
    """ Acts as a file object for writing chunks of serialized data
        to file. Prepends each chunk with:
        chunk length in bytes (4 bytes)
        and a crc32 hash      (4 bytes)
    """

    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, "wb")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def write(self, data: bytes):
        """
        """
        self.file.write(header.pack(len(data), binascii.crc32(data)))
        self.file.write(data)


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
            rd = fh.read(header.size)
            if rd == b"":
                break
            self.fpos.append(fp)
            offset, crc = header.unpack(rd)
            self.n_entries += 1
            fp = fh.tell() + offset
        self.file.seek(0)

    def read(self) -> bytes:
        sized = self.file.read(header.size)
        if sized == b"":
            return None
        size, crc = sizeform.unpack(sized)[0]
        return self.file.read(size)


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
