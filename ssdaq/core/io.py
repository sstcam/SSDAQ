import struct
import binascii
from .utils import get_si_prefix
from datetime import datetime
import os
from typing import Union
import numpy as np
import bz2

_chunk_header = struct.Struct("<2I")
_file_header = struct.Struct("<Q4I")

###Raw object IO classes#####


class RawObjectWriterBase:
    """ Base class of a file object for
        writing indexable chunks of serialized data
        to file.
    """

    _protocols = {}

    def __init__(self, filename: str, protocol:int=1, compressor="bz2", **kwargs):
        """Summary

        Args:
            filename (str): Description
            protocol (int, optional): Description
            compressor (str, optional): Description
            **kwargs: Description
        """
        self._writer = RawObjectWriterBase._protocols[protocol](
            filename, compressor=compressor, **kwargs
        )
        self.protocol = protocol

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._writer.close()

    def write(self, data: bytes):
        """ Writes a stream of bytes to file

            args:
                data (bytes): bytes to be writen to file
        """
        self._writer.write(data)

    def close(self):
        """ Closes the file handle
        """
        self._writer.close()

    @classmethod
    def _register(cls, scls):
        cls._protocols[scls._protocol_v] = scls
        return scls

    @property
    def data_counter(self)->int:
        """Counter of the number of objects written to file

        Returns:
            int
        """
        return self._writer.data_counter


@RawObjectWriterBase._register
class RawObjectWriterV0:
    """ Acts as a file object for writing chunks of serialized data
        to file. Prepends each chunk with:
        chunk length in bytes (4 bytes)
        and a crc32 hash      (4 bytes)

        The file header is 24 bytes long and has the following layout

            bytes:      field:
            0-7         Custom field for file format specifications (set by the header parameter)
            8-11        Protocol version
            12-15       Not used
            16-19       Not used
            20-23       Not used

        General file structure:
            +-------------+
            | File Header |
            +-------------+
            | Chunk Header|
            +-------------+
            |     Data    |
            +-------------+
            | Chunk Header|
            +-------------+
            |     Data    |
            +-------------+
                  ...
                  ...

    """

    _protocol_v = 0

    def __init__(self, filename: str, header: int = 0):
        self.filename = filename
        self.file = open(self.filename, "wb")
        self.data_counter = 0
        self.version = 0
        self.file.write(_file_header.pack(header, self.version, 0, 0, 0))
        # self.protocol = protocol

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


@RawObjectWriterBase._register
class RawObjectWriterV1:
    """ An Indexed container file.

    """

    _protocol_v = 1
    _file_header = struct.Struct("<4s4sIQ2H")
    _bunch_trailer_header = struct.Struct("<3Q2IH")
    _compressors = {"bz2": (bz2, 1)}

    def __init__(
        self,
        filename: str,
        header_ext: bytes = None,
        marker_ext: str = "",
        compressor=None,
        bunchsize: int = 1000000,
    ):
        """Summary

        Args:
            filename (str): Description
            header_ext (bytes, optional): Description
            marker_ext (str, optional): Description
            compressor (None, optional): Description
            bunchsize (int, optional): Description
        """
        self.filename = filename
        self._file = open(self.filename, "wb")

        self.compress = False
        compressor_id = 0
        if compressor is not None:
            self.compress = True
            self.compressor = RawObjectWriterV1._compressors[compressor][0]
            compressor_id = RawObjectWriterV1._compressors[compressor][1]

        self.data_counter = 0
        self.version = RawObjectWriterV1._protocol_v
        self.time_stamp = int(datetime.now().timestamp())
        self.bunchsize = bunchsize
        self._fp = 0
        self._marker_ext = marker_ext
        header_ext = header_ext or []
        self._write(
            RawObjectWriterV1._file_header.pack(
                "SOF".encode(),
                marker_ext.encode(),
                self.version,
                self.time_stamp,
                compressor_id,
                len(header_ext),
            )
        )

        if len(header_ext) > 0:
            self._write(header_ext)
        self._buffer = []
        self._cbunchindex = []
        self._cbunchoffset = 0
        self._last_bunch_fp = 0
        self._bunch_number = 0

    def _write(self, data: bytes):
        self._file.write(data)
        self._fp += len(data)

    def write(self, data: bytes):
        """ Writes a stream of bytes to file

            args:
                data (bytes): bytes to be writen to file
        """

        self._buffer.append(data)
        self._cbunchindex.append((binascii.crc32(data), len(data)))
        self._cbunchoffset += len(data)
        self.data_counter += 1
        if self._cbunchoffset > self.bunchsize:
            self.flush()

    def flush(self):
        if len(self._buffer) < 1:
            return
        bunch_start_fp = self._fp
        # writing the data bunch
        if self.compress:
            byte_buff = bytearray()
            for data in self._buffer:
                byte_buff.extend(data)
            self._write(self.compressor.compress(byte_buff))
        else:
            for data in self._buffer:
                self._write(data)

        # constructing the index and writing it in the bunch trailer
        index = list(zip(*self._cbunchindex))
        n = len(self._buffer)
        bunch_index = struct.pack("{}I{}I".format(n, n), *index[0], *index[1])
        self._write(bunch_index)

        bunch_crc = 0
        bunch_index_trailer = RawObjectWriterV1._bunch_trailer_header.pack(
            self._fp - self._last_bunch_fp,
            self._fp - bunch_start_fp,
            self._fp,
            bunch_crc,
            len(self._buffer),
            self._bunch_number,
        )

        # before writing the bunch trailer we update
        # the file pointer for the last bunch
        self._last_bunch_fp = self._fp

        self._write(bunch_index_trailer)

        # reseting/updating the last bunch descriptors
        self._cbunchindex.clear()
        self._buffer.clear()
        self._cbunchoffset = 0
        self._bunch_number += 1

    def close(self):
        self.flush()
        self._file.close()


class RawObjectReaderBase:
    """This class

    Attributes:
        file (TYPE): Description
        filename (TYPE): Description
        metadata (dict): Description
    """

    _protocols = {}

    def __init__(self, filename: str):
        """ Reads Streamed Object Files

        Args:
            filename (str): filename and path to the file

        Raises:
            TypeError: Raised if the file is not recognized as SOF
        """

        self.filename = filename
        self.file = open(self.filename, "rb")
        self._fhead = self.file.read(12)  # _file_header.size)
        self.file.seek(0)
        self.metadata = {}

        self.fhead, self.version = struct.unpack("QI", self._fhead)

        if self.version == 0 and self.fhead >= 0:
            readerclass = RawObjectReaderBase._protocols[self.version]
            self._reader = readerclass(self.file)
        elif self.version > 0:
            readerclass = RawObjectReaderBase._protocols[self.version]
            self._fhead = self.file.read(readerclass._file_header.size)
            # marker,extmarker,self.version,self.timestamp,self.compressed,self.lenheadext = readerclass._file_header.unpack(self._fhead)
            self._reader = readerclass(self.file)
        else:
            raise TypeError("This file appears not to be a stream object file (SOF)")

    @classmethod
    def _register(cls, scls):
        cls._protocols[scls._protocol_v] = scls
        return scls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

    def reload(self):
        """ Reload the index table. Useful if the file
            is being written too when read
        """
        self._reader.reload()

    def resetfp(self):
        """ Resets file pointer to the first object in file
        """
        self._reader.resetfp()

    def __getitem__(self, ind: Union[int, slice, list]):
        """Indexing interface to the streamed file.
        Objects are read by their index, slice or list of indices.

        Args:
            ind (Union[int, slice, list]): Description

        Returns:
            TYPE: Description
        """
        if isinstance(ind, slice):
            data = [self.read_at(ii) for ii in range(*ind.indices(self.n_entries))]
            return data
        elif isinstance(ind, list):
            data = [self.read_at(ii) for ii in ind]
            return data
        elif isinstance(ind, int):
            return self.read_at(ind)

    def read_at(self, ind: int) -> bytes:
        """Reads one object at the index indicated by `ind`

        Args:
            ind (int): the index of the object to be read

        Returns:
            bytes: that represent the object

        Raises:
            IndexError: if index out of range
        """
        return self._reader.read_at(ind)

    def read(self) -> bytes:
        """ Reads one object at the position of the file pointer.

            Returns:
                bytes: Bytes that represent the object
        """
        return self._reader.read()

    def close(self):
        """ closes file handle
        """
        self.file.close()

    @property
    def n_entries(self)->int:
        """ number of objects in file.

        Returns:
            int: file object count
        """
        return self._reader.n_entries

    @property
    def filesize(self)->int:
        """ the file size on disk in bytes

        Returns:
            int: file size
        """
        return self._reader.filesize

    @property
    def timestamp(self)->datetime:
        """ unix timestamp of the file creation time

        Returns:
            datetime.datetime: creation datetime
        """
        return datetime.fromtimestamp(self._reader._timestamp)

    def __str__(self):

        s = "{}:\n".format(self.__class__.__name__)
        s += "filename: {}\n".format(self.filename)
        s += "timestamp: {}\n".format(self.timestamp)
        s += "n_entries: {}\n".format(self._reader.n_entries)
        s += "file size: {} {}B\n".format(*get_si_prefix(self._reader.filesize))
        for k, v in self.metadata.items():
            s += "{}: {}\n".format(k, v)
        s += "file format version: {}".format(self.version)
        return s


@RawObjectReaderBase._register
class RawObjectReaderV1:
    _protocol_v = 1
    _file_header = struct.Struct("<4s4sIQ2H")
    _bunch_trailer_header = struct.Struct("<3Q2IH")
    _file_trailer = struct.Struct("<4s4sIQ")
    _compressors = {"bz2": (bz2, 1)}

    def __init__(self, file):
        fileheader_def = RawObjectReaderV1._file_header
        self.file = file
        self.file.seek(0)
        fileheader = self.file.read(fileheader_def.size)
        marker, extmarker, self._version, self._timestamp, self._compressed, self._lenheadext = fileheader_def.unpack(
            fileheader
        )
        if marker[:3].decode() != "SOF":
            raise TypeError("This file appears not to be a stream object file (SOF)")
        if self._version != RawObjectReaderV1._protocol_v:
            raise TypeError(
                "This file is written with protocol V{}"
                " while this class reads protocol V{}".format(
                    self._version, RawObjectReaderV1._protocol_v
                )
            )
        self._compressor = None
        if self._compressed > 0:
            compressorsr = {}
            for k, v in RawObjectReaderV1._compressors.items():
                compressorsr[v[1]] = (v[0], k)
            self._compressor = compressorsr[self._compressed][0]
            self._compressor_name = compressorsr[self._compressed][1]
        self._headext = None
        if self._lenheadext > 0:
            self._headext = self.file.read(self._lenheadext)
        self._fp_start = self.file.tell()
        self.n_bunches = None
        self.n_entries = None
        self.filesize = None
        self._rawindex = {}
        self._bunch_buffer = {}
        self._current_index = 0
        self._scan_file()

    def _scan_file(self):
        from collections import namedtuple

        BunchTrailer = namedtuple(
            "BunchTrailer", "bunchoff dataoff fileoff crc bunchsize ndata index objsize"
        )
        self.file.seek(-RawObjectReaderV1._bunch_trailer_header.size, os.SEEK_END)

        self.filesize = self.file.tell()
        self.file_index = [0]
        while self.file.tell() > self._fp_start:
            # read bunch trailer
            last_bunch_trailer = self.file.read(
                RawObjectReaderV1._bunch_trailer_header.size
            )
            bunchoff, dataoff, fileoff, crc, ndata, bunch_n = RawObjectReaderV1._bunch_trailer_header.unpack(
                last_bunch_trailer
            )
            # read bunch index
            self.file.seek(
                self.file.tell()
                - RawObjectReaderV1._bunch_trailer_header.size
                - ndata * 2 * 4
            )
            index = struct.unpack(
                "{}I{}I".format(ndata, ndata), self.file.read(ndata * 2 * 4)
            )
            objsize = np.array(index[ndata:], dtype=np.uint32)
            self._rawindex[(0, bunch_n)] = BunchTrailer(
                bunchoff,  # Offset to earlier bunch or file header if first bunch
                dataoff,  # Offset to beginning of data in bunch
                fileoff,  # Offset to beginning of file
                crc,  # bunch crc
                dataoff - ndata * 2 * 4,  # Size of data bunch
                ndata,  # number of objects in bunch
                [0] + list(np.cumsum(objsize[:-1])),  # Object offsets in bunch
                objsize,  # object sizes
            )
            self.file.seek(self.file.tell() - bunchoff)

        self._index = []
        self._bunch_index = {}
        for k, bunch in sorted(self._rawindex.items()):
            self._bunch_index[k] = (bunch.fileoff - bunch.dataoff, bunch.bunchsize)
            for i, obj in enumerate(bunch.index):
                self._index.append((k, int(obj), int(bunch.objsize[i])))
        self.n_entries = len(self._index)

    def _get_bunch(self, bunch_id):
        if bunch_id in self._bunch_buffer:
            return self._bunch_buffer[bunch_id]
        else:
            self.file.seek(self._bunch_index[bunch_id][0])
            bunch = self._compressor.decompress(
                self.file.read(
                    self.file_index[bunch_id[0]] + self._bunch_index[bunch_id][1]
                )
            )
            self._bunch_buffer[bunch_id] = bunch
            return bunch

    def read_at(self, ind: int) -> bytes:
        """Reads one object at the index indicated by `ind`

        Args:
            ind (int): the index of the object to be read

        Returns:
            bytes: that represent the object

        Raises:
            IndexError: if index out of range
        """

        if ind > self.n_entries - 1:
            raise IndexError(
                "The requested file object ({}) is out of range".format(ind)
            )
        obji = self._index[ind]
        if self._compressed:
            bunch = self._get_bunch(obji[0])
            return bunch[obji[1] : obji[1] + obji[2]]
        else:
            fpos = self.file_index[obji[0][0]] + self._bunch_index[obji[0]][0] + obji[1]
            self.file.seek(fpos)

            return self.file.read(obji[2])

    def resetfp(self):
        """ Resets file pointer to the first object in file
        """
        self._current_index = 0

    def read(self) -> bytes:
        """ Reads one object at the position of the file pointer.

            Returns:
                bytes: Bytes that represent the object
        """
        self._current_index += 1
        return self.read_at(self._current_index - 1)


@RawObjectReaderBase._register
class RawObjectReaderV0:

    _protocol_v = 0

    def __init__(self, file):
        self.file = file
        self._scan_file()
        self._timestamp = 0

    def reload(self):
        """ Reload the index table. Useful if the file
            is being written too when read
        """
        self._scan_file(self.filesize, self.n_entries, self.fpos)

    def resetfp(self):
        """ Resets file pointer to the first object in file
        """
        self.file.seek(_file_header.size)

    def _scan_file(self, offset=0, n_entries=0, fpos=[]):
        """Summary

        Args:
            offset (int, optional): Description
            n_entries (int, optional): Description
            fpos (list, optional): Description
        """
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

    def read_at(self, ind: int) -> bytes:
        """Reads one object at the index indicated by `ind`

        Args:
            ind (int): the index of the object to be read

        Returns:
            bytes: that represent the object

        Raises:
            IndexError: if index out of range
        """
        if ind > len(self.fpos) - 1:
            raise IndexError(
                "The requested file object ({}) is out of range".format(ind)
            )
        self.file.seek(self.fpos[ind])
        return self.read()

    def read(self) -> bytes:
        """ Reads one object at the position of the file pointer.

            Returns:
                bytes: Bytes that represent the object
        """
        sized = self.file.read(_chunk_header.size)
        if sized == b"":
            return None
        size, crc = _chunk_header.unpack(sized)
        return self.file.read(size)


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
        """ Initialize a BaseFileWriter

        Args:
            file_prefix (str): The filename prefix (not path)
            writer (TYPE): A writer class
            file_ext (str): File extension to be used
            folder (str, optional): Path to folder where the file should be saved
            file_enumerator (str, optional): A string that sets which filename enumeration to use (if None no enumeration is used)
            filesize_lim (int, optional): If file size is above this limit a new file is open (if None no limit is imposed)
        """
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
        """ Internal method to open a new file
        """
        self.file_data_counter = 0
        if self.file_enumerator == "date":
            suffix = datetime.utcnow().strftime("%Y-%m-%d_%H%M")
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
        """ Internal method to close the current open file
        """
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
        """ A callback method which starts a new file when True is returned

        Args:
            data (): received data

        Returns:
            bool: if true a new file will be started
        """
        return False

    def _start_new_file(self):
        """ Internal method to start a new file.

            The current file is closed and the file counter is incremented
            the new file is opened.
        """
        self._close_file()
        self.file_counter += 1
        self._open_file()

    def write(self, data):
        """ Write data to file

        Args:
            data (TYPE): The data to be written to file
        """

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
        """ Closes the file writer
        """
        self._close_file()
        self.log.info(
            "FileWriter has written a"
            " total of %d events to %d file(s)" % (self.data_counter, self.file_counter)
        )
