import struct
import binascii
from .utils import get_si_prefix

_chunk_header = struct.Struct("2I")
_file_header = struct.Struct("Q4I")
###Raw object IO classes#####


class RawObjectWriterBase:
    """ Acts as a file object for writing chunks of serialized data
        to file. Prepends each chunk with:
        chunk length in bytes (4 bytes)
        and a crc32 hash      (4 bytes)
    """

    def __init__(self, filename: str, header: int = 0):
        self.filename = filename
        self.file = open(self.filename, "wb")
        self.data_counter = 0
        self.version = 0
        self.file.write(_file_header.pack(header, self.version, 0, 0, 0))

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
        self._fhead = self.file.read(_file_header.size)
        self.file.seek(0)
        self.fhead = self._fhead[0]
        self.version = self._fhead[1]
        # self._chunk_header = struct.Struct("2I")
        self._scan_file()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def reload(self):
        self.file.seek(0)
        self._scan_file()

    def _scan_file(self):
        self.file.seek(0)
        fh = self.file
        self.n_entries = 0
        self.fpos = []
        # Skipping file header
        fp = _file_header.size
        while True:
            fh.seek(fp)
            rd = fh.read(_chunk_header.size)
            if rd == b"":
                break
            self.fpos.append(fp)
            offset, crc = _chunk_header.unpack(rd)
            self.n_entries += 1
            fp = fh.tell() + offset
        self.file.seek(_file_header.size)
        self.filesize = self.fpos[-1] + offset

    def read(self) -> bytes:
        sized = self.file.read(_chunk_header.size)
        if sized == b"":
            return None
        size, crc = _chunk_header.unpack(sized)
        return self.file.read(size)

    def close(self):
        self.file.close()

    def __str__(self):

        s = "{}:\n".format(self.__class__.__name__)
        s += "filename: {}\n".format(self.filename)
        s += "n_entries: {}\n".format(self.n_entries)
        s += "file size: {} {}B".format(*get_si_prefix(self.filesize))
        return s


###End of Raw object IO classes#####
