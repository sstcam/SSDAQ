import struct
import binascii
from .utils import get_si_prefix
from datetime import datetime
import os
_chunk_header = struct.Struct("<2I")
_file_header = struct.Struct("<Q4I")
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
        """ Writes a stream of bytes to file

            args:
                data (bytes): bytes to be writen to file
        """
        self.file.write(_chunk_header.pack(len(data), binascii.crc32(data)))
        self.file.write(data)
        self.data_counter += 1

    def close(self):
        self.file.close()


class RawObjectReaderBase:
    """This class
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
        self._scan_file(self.filesize,self.n_entries,self.fpos)

    def resetfp(self):
        self.file.seek(_file_header.size)

    def __getitem__(self, ind):
        if isinstance(ind, slice):
            data = [self.read_at(ii) for ii in range(*ind.indices(self.n_entries))]
            return data
        elif isinstance(ind, list):
            data = [self.read_at(ii) for ii in ind]
            return data
        elif isinstance(ind, int):
            return self.read_at(ind)


    def _scan_file(self,offset=0,n_entries=0,fpos=[]):
        self.file.seek(offset)
        fh = self.file
        self.n_entries = n_entries
        self.fpos = fpos
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

    def read_at(self,pos:int) -> bytes:
        if pos > len(self.fpos)-1:
            raise IndexError("The requested file object ({}) is out of range".format(pos))
        self.file.seek(self.fpos[pos])
        return self.read()

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

class BaseFileWriter:
    """
    A data file writer wrapper class that handles filename enumerators and size limits.

    Filename enumerators can be date-time or order starting at ``000``.
    A new file is started if the preceeding file exceeds the filesize
    limit or if the method ``data_cond()`` returns true. This method may
    be overidden by inheriting classes


    """

    def __init__(
        self,
        file_prefix: str,
        writer,
        file_ext: str,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):

        self.file_enumerator = file_enumerator
        self.folder = folder
        self.file_prefix = file_prefix
        # self.log = sslogger.getChild(self.__class__.__name__)
        self.data_counter = 0
        self.file_counter = 1
        self.filesize_lim = ((filesize_lim or 0) * 1024 ** 2) or None
        self._writercls = writer
        # self.log = writer.log
        self.file_ext = file_ext
        self._open_file()

    def _open_file(self):

        self.file_data_counter = 0
        if self.file_enumerator == "date":
            suffix = datetime.utcnow().strftime("%Y-%m-%d.%H:%M")
        elif self.file_enumerator == "order":
            suffix = "%0.3d" % self.file_counter
        else:
            suffix = ""

        self.filename = os.path.join(
            self.folder, self.file_prefix + suffix + self.file_ext
        )
        self._writer = self._writercls(self.filename)
        self.log.info("Opened new file, will write events to file: %s" % self.filename)

    def _close_file(self):

        from ssdaq.utils.file_size import convert_size

        self.log.info("Closing file %s" % self.filename)
        self._writer.close()
        self.log.info(
            "FileWriter has written %d events in %g%sB to file %s"
            % (
                self._writer.data_counter,
                *get_si_prefix(os.stat(self.filename).st_size),
                self.filename,
            )
        )

    def data_cond(self, data):
        return False

    def _start_new_file(self):
        self._close_file()
        self.file_counter += 1
        self._open_file()

    def write(self, data):
        # Start a new file if self.data_cond(data) returns true
        if self.data_cond(data) and self.data_counter > 0:
            self._close_file()
            self.file_counter += 1
            self._open_file()
        elif self.filesize_lim is not None:
            if (
                self.data_counter % 100 == 0
                and os.stat(self.filename).st_size > self.filesize_lim
            ):
                self._close_file()
                self.file_counter += 1
                self._open_file()

        self._writer.write(data)
        self.data_counter += 1

    def close(self):
        self._close_file()
        self.log.info(
            "FileWriter has written a"
            " total of %d events to %d file(s)" % (self.data_counter, self.file_counter)
        )