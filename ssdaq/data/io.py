### Specialization to different protobuf protocols#####
from . import LogData
from . import TriggerMessage
from . import TriggerPacketData, NominalTriggerDataEncode
from ssdaq.core.io import RawObjectWriterBase, RawObjectReaderBase


class LogWriter(RawObjectWriterBase):
    def __init__(self, filename: str):
        super().__init__(filename, header=1)

    def write(self, log: LogData):
        super().write(log.SerializeToString())


class LogReader(RawObjectReaderBase):
    def read(self):
        log = LogData()
        data = super().read()
        log.ParseFromString(data)
        return log


class TimestampWriter(RawObjectWriterBase):
    def __init__(self, filename: str):
        super().__init__(filename, header=2)

    def write(self, timestamp):
        super().write(timestamp.SerializeToString())


class TimestampReader(RawObjectReaderBase):
    def read(self):
        timestamp = TriggerMessage()
        data = super().read()
        timestamp.ParseFromString(data)
        return timestamp


class TriggerWriter(RawObjectWriterBase):
    def __init__(self, filename: str):
        super().__init__(filename, header=3)

    def write(self, trigg):
        super().write(
            NominalTriggerDataEncode.pack(
                trigg.TACK,
                trigg.trigg,
                trigg.uc_ev,
                trigg.uc_pps,
                trigg.uc_clock,
                trigg.type,
            )
        )


# Manually list unpackers for now
class TriggerReader(RawObjectReaderBase):
    def read(self):
        return TriggerPacketData.unpack(super().read())


def log_unpack(data):
    log = LogData()
    log.ParseFromString(data)
    return log


def timestamp_unpack(data):
    timestamp = TriggerMessage()
    timestamp.ParseFromString(data)
    return timestamp


_unpackers = [log_unpack, timestamp_unpack, TriggerPacketData.unpack]


class DataReader(RawObjectReaderBase):
    def __init__(self, filename):
        super().__init__(filename)
        if self.fhead == 0 or self.fhead > len(_unpackers):
            raise ValueError("No compatible reader found for this file...")
        self._unpack = _unpackers[self.fhead - 1]

    def read(self):
        return self._unpack(super().read())


import numpy as np
import tables
from tables import IsDescription, UInt64Col, Float32Col, Float64Col
from collections import namedtuple as _nt
from ssdaq.version import get_version
from .slowsignal_format import SSReadout, N_TM_PIX, N_TM, ss_mappings


class TelData(IsDescription):
    db_t = Float64Col()
    db_t_s = UInt64Col()
    db_t_ns = UInt64Col()
    ra = Float64Col()
    dec = Float64Col()


class SSReadoutTableDs(IsDescription):
    iro = UInt64Col()  # readout numner/index
    time = UInt64Col()  # TACK timestamp
    cpu_t = Float64Col()  # native python timestamp float64
    cpu_t_s = UInt64Col()  # seconds time stamp uint64
    cpu_t_ns = UInt64Col()  # nano seconds time stamp uint64
    data = Float32Col((N_TM, N_TM_PIX))  # 2D data array containing


class SSDataWriter(object):
    """A writer for Slow Signal data"""

    def __init__(
        self,
        filename: str,
        attrs: dict = None,
        filters: tables.Filters = None,
        buffer: int = 1,
        tel_table=True,
    ):

        self.filename = filename
        filters = (
            filters
            if filters != None
            else tables.Filters(
                complevel=9,
                complib="bzip2",  # gives us 5 times the speed for the same compression as zlib
                fletcher32=True,
            )
        )
        self.file = tables.open_file(
            self.filename,
            mode="w",
            title="CHEC-S Slow signal monitor data",
            filters=filters,
        )
        self.group = self.file.create_group(
            self.file.root, "SlowSignal", "Slow signal data"
        )
        self.table = self.file.create_table(
            self.group, "readout", SSReadoutTableDs, "Slow signal readout"
        )
        self.tel_table = None
        self.tables = [self.table]

        if tel_table:
            self.tel_table = self.file.create_table(
                self.group, "tel_table", TelData, "Telescope data"
            )
            self.tel_row = self.tel_table.row
            self.tables.append(self.tel_table)

        self.ro_row = self.table.row
        self.readout_counter = 0
        self.buffer = buffer
        self._cur_buf = 0
        if attrs is not None:
            for k, v in attrs.items():
                self.table.attrs[k] = v
        self.table.attrs["ss_data_version"] = 0
        self.table.attrs["ssdaq_version"] = get_version(pep440=True)
        self.table.attrs["ssl2asic_ch"] = ss_mappings.ssl2asic_ch

    def write_tel_data(self, ra, dec, time, seconds, ns):
        self.tel_row["db_t"] = time
        self.tel_row["db_t_s"] = seconds
        self.tel_row["db_t_ns"] = ns
        self.tel_row["ra"] = ra
        self.tel_row["dec"] = dec
        self.tel_row.append()

    def write_readout(self, ro):

        self.ro_row["iro"] = ro.iro
        self.ro_row["time"] = ro.time
        self.ro_row["cpu_t"] = ro.cpu_t
        self.ro_row["cpu_t_s"] = ro.cpu_t_s
        self.ro_row["cpu_t_ns"] = ro.cpu_t_ns
        self.ro_row["data"] = np.asarray(ro.data, dtype=np.float32)

        self.ro_row.append()
        self._cur_buf += 1
        if self._cur_buf >= self.buffer:
            self._flush()
            self._cur_buf = 0

        self.readout_counter += 1

    def _flush(self):
        for table in self.tables:
            table.flush()

    def close_file(self):
        """Closes file handle
        """
        self._flush()
        self.file.close()


class SSDataReader(object):
    """A reader for Slow Signal data"""

    def __init__(self, filename, mapping="ssl2asic_ch"):
        """

            Args:
                filename (str): path to file

            Kwargs:
                mapping (str): determines how the pixels are mapped. Two mappings
                               are availabe: 'ssl2colrow' and 'ssl2asic_ch' which correspond to
                               a 2D col-row layout and ASIC-channel which is the same ordering used for the
                               fast signal data.


        """
        self.filename = filename
        self.file = tables.open_file(self.filename, mode="r")

        self.raw_data = np.zeros((N_TM, N_TM_PIX), dtype=np.float32)
        self.data = np.zeros((N_TM, N_TM_PIX), dtype=np.float32)
        self.iro = None
        self.time = None
        self.cpu_t = None

        self._readversions = {0: self._read0}
        self.attrs = self.file.root.SlowSignal.readout.attrs

        try:
            self.map = ss_mappings.__getattribute__(mapping)
        except:
            raise ValueError("No mapping found with name %s" % mapping)

        if "ss_data_version" not in self.attrs:
            raise RuntimeError(
                "This is probably a pre v0.9.0 file which is not supported anymore"
            )
        else:
            self._read = self._readversions[self.attrs.ss_data_version]

    def __iter__(self, start=None, stop=None, step=None):
        return read(start, stop, step)

    def __getitem__(self, iro):

        if isinstance(iro, slice):
            ro_list = [self[ii] for ii in range(*iro.indices(self.n_readouts))]
            return np.array(ro_list)
        elif isinstance(iro, list):
            ro_list = [self[ii] for ii in iro]
            return np.array(ro_list)
        elif isinstance(iro, int):
            if iro < 0:
                iro += self.n_events
            if iro < 0 or iro >= len(self):
                raise IndexError("The requested event ({}) is out of range".format(iro))
            return np.copy(self.read(iro).__next__())
        else:
            raise TypeError("Invalid argument type")

    def __len__(self):
        return self.n_readouts

    def read(self, start=None, stop=None, step=None):
        """ A data file iterator for reading data rows.

            Args:
                start (int): starting row number
                stop  (int): stopping row number
                step  (int): size of the step at each iteration
        """

        if stop is None and start is not None:
            stop = start + 1
        return self._read(start, stop, step)

    def _read0(self, start=None, stop=None, step=None):
        for r in self.file.root.SlowSignal.readout.iterrows(start, stop, step):
            self.raw_data[:] = r["data"]
            self.data[:] = r["data"][:, self.map]
            self.iro = r["iro"]
            self.time = r["time"]
            self.cpu_t = r["cpu_t"]
            self.cpu_t_s = r["cpu_t_s"]
            self.cpu_t_ns = r["cpu_t_ns"]
            yield self.data

    @property
    def n_readouts(self):
        return self.file.root.SlowSignal.readout.nrows

    @property
    def ssreadout(self):
        return SSReadout(self.time, self.iro, data=self.raw_data, cpu_t=self.cpu_t)

    def load_all_data(self, tm, calib=None, mapping=None):
        """ Loads all rows of data for a particular target moduel into memory (in the future a selection of modules)

            Args:
                tm (int):   The slot number of the target module

            Kwargs:
                calib (arraylike): an array with calibration coefficient that should be applied to the data
                mapping (str or arraylike): a string to select a mapping  or an array with the mapping
                                            ['ssl2colrow','ssl2asic_ch','raw']
        """
        if calib is None:
            calib = 1.0
        if mapping is None:
            mapping = self.map
        elif isinstance(mapping, str):
            if mapping == "raw":
                mapping = np.arange(N_TM_PIX)
            else:
                try:
                    mapping = ss_mappings.__getattribute__(mapping)
                except:
                    raise ValueError("No mapping found with name %s" % mapping)

        amps = np.zeros((self.n_readouts, N_TM_PIX))
        time = np.zeros(self.n_readouts, dtype=np.uint64)
        cpu_t = np.zeros(self.n_readouts)
        iro = np.zeros(self.n_readouts, dtype=np.uint64)

        for i, r in enumerate(self.read()):
            amps[i, :] = self.raw_data[tm, :] * calib
            time[i] = self.time
            cpu_t[i] = self.cpu_t
            iro[i] = self.iro

        amps = amps[:, mapping]

        ssdata = _nt("ssdata", "iro amps time cpu_t tm")
        return ssdata(iro, amps, time, cpu_t, tm)

    def load_as_pd_table(self):
        import pandas as pd

        data = []
        for r in self.read():
            amps = r.flatten()  # self.data.flatten()
            for i in range(2048):
                data.append(
                    {
                        "iro": self.iro,
                        "time": self.time,
                        "cpu_t": self.cpu_t,
                        "pix": i,
                        "amp": amps[i],
                    }
                )
        df = pd.DataFrame(data)
        df.set_index(["iro", "pix"], inplace=True)  #
        return df

    def __repr__(self):
        return repr(self.file)

    def __str__(self):
        s = "SSDataReader:\n"
        s += "    Filename:%s\n" % self.filename
        s += "    Title: CHEC-S Slow signal monitor data\n"
        s += "    n_readouts: %d\n" % self.n_readouts
        s += "    ssdata-version: %d\n" % self.attrs.ss_data_version

        return s

    def close_file(self):
        """Closes file handle
        """
        self.file.close()
