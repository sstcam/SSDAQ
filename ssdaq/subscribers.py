import logging
import os
from datetime import datetime
from threading import Thread
from ssdaq import sslogger
from ssdaq.core.basicsubscriber import BasicSubscriber, WriterSubscriber
from ssdaq import logging as handlers
from ssdaq.data import io, TriggerPacketData, CDTS_pb2, monitor_pb2, SSReadout
from ssdaq.core.utils import get_si_prefix

class SSReadoutSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=SSReadout.from_bytes)


class BasicTriggerSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=TriggerPacketData.unpack)


logunpack = lambda x: handlers.protb2logrecord(handlers.parseprotb2log(x))


class BasicLogSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=logunpack)


def timeunpack(x):
    tmsg = CDTS_pb2.TriggerMessage()
    tmsg.ParseFromString(x)
    return tmsg


class BasicTimestampSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=timeunpack)


def monunpack(x):
    monmsg = monitor_pb2.MonitorData()
    monmsg.ParseFromString(x)
    return monmsg


class BasicMonSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=monunpack)


logprotounpack = lambda x: handlers.parseprotb2log(x)


class LogProtoSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=logprotounpack)


# These are locals in init that we want to skip
# when creating the kwargs dict
skip = ["self", "__class__"]


class LogWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):
        super().__init__(
            subscriber=LogProtoSubscriber,
            writer=io.LogWriter,
            file_ext=".prt",
            name="LogWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )


class TimestampWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):

        super().__init__(
            subscriber=BasicTimestampSubscriber,
            writer=io.TimestampWriter,
            file_ext=".prt",
            name="TimestampWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )
        print(locals())


class TriggerWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):
        super().__init__(
            subscriber=BasicTriggerSubscriber,
            writer=io.TriggerWriter,
            file_ext=".prt",
            name="TriggerWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )


class SSFileWriter(Thread):
    """
    A data file writer for slow signal data.

    This class uses a instance of a SSReadoutSubscriber to receive readouts and
    an instance of SSDataWriter to write an HDF5 file to disk.
    """

    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):

        Thread.__init__(self)
        self.file_enumerator = file_enumerator
        self.folder = folder
        self.file_prefix = file_prefix
        self.log = sslogger.getChild("SSFileWriter")
        self._readout_subscriber = SSReadoutSubscriber(
            logger=self.log.getChild("Subscriber"), ip=ip, port=port
        )
        self.running = False
        self.readout_counter = 0
        self.file_counter = 1
        self.filesize_lim = ((filesize_lim or 0) * 1024 ** 2) or None
        self._open_file()

    def _open_file(self):


        self.file_readout_counter = 0
        if self.file_enumerator == "date":
            suffix = datetime.utcnow().strftime("%Y-%m-%d_%H.%M")
        elif self.file_enumerator == "order":
            suffix = "%0.3d" % self.file_counter
        else:
            suffix = ""

        self.filename = os.path.join(self.folder, self.file_prefix + suffix + ".hdf5")
        self._writer = io.SSDataWriter(self.filename)
        self.log.info("Opened new file, will write events to file: %s" % self.filename)

    def _close_file(self):
        self.log.info("Closing file %s" % self.filename)
        self._writer.close_file()
        self.log.info(
            "FileWriter has written %d events in %g%sB to file %s"
            % (
                self._writer.readout_counter,
                *get_si_prefix(os.stat(self.filename).st_size),
                self.filename,
            )
        )

    def close(self):
        self.running = False
        self._readout_subscriber.close()
        self.join()

    def run(self):
        self.log.info("Starting writer thread")
        self._readout_subscriber.start()
        self.running = True
        while self.running:
            readout = self._readout_subscriber.get_data()
            if readout == None:
                continue
            # Start a new file if we get
            # an readout with readout number 1
            if readout.iro == 1 and self.readout_counter > 0:
                self._close_file()
                self.file_counter += 1
                self._open_file()
            elif self.filesize_lim is not None:
                if (
                    self.readout_counter % 100 == 0
                    and os.stat(self.filename).st_size > self.filesize_lim
                ):
                    self._close_file()
                    self.file_counter += 1
                    self._open_file()

            self._writer.write_readout(readout)
            self.readout_counter += 1

        self.log.info("Stopping Subscriber thread")
        self._readout_subscriber.close()
        self._close_file()
        self.log.info(
            "SSFileWriter has written a"
            " total of %d events to %d file(s)"
            % (self.readout_counter, self.file_counter)
        )
