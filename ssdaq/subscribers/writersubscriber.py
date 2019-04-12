from ssdaq import SSReadout

from ssdaq import SSDataWriter
from threading import Thread
from ssdaq import sslogger

from ssdaq import BasicSubscriber
import logging
import os
from ssdaq.core.logging import handlers
from ssdaq.core.io import protobuf_io
from ssdaq.subscribers.basicsubscriber import (
    BasicTimestampSubscriber,
    BasicTriggerSubscriber,
)


class WriterSubscriber(Thread):
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
        subscriber: BasicSubscriber,
        writer,
        file_ext: str,
        name: str,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):

        Thread.__init__(self)
        self.file_enumerator = file_enumerator
        self.folder = folder
        self.file_prefix = file_prefix
        self.log = sslogger.getChild(name)
        self._subscriber = subscriber(
            logger=self.log.getChild("Subscriber"), ip=ip, port=port
        )
        self.running = False
        self.data_counter = 0
        self.file_counter = 1
        self.filesize_lim = None if filesize_lim is None else filesize_lim * 1024 ** 2
        self._writercls = writer
        self.file_ext = file_ext
        self._open_file()

    def _open_file(self):
        from datetime import datetime

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
            "SSFileWriter has written %d events in %s bytes to file %s"
            % (
                self._writer.data_counter,
                convert_size(os.stat(self.filename).st_size),
                self.filename,
            )
        )

    def close(self):
        self.running = False
        self._subscriber.close()
        self.join()

    def data_cond(self, data):
        return False

    def run(self):
        self.log.info("Starting writer thread")
        self._subscriber.start()
        self.running = True
        while self.running:

            data = self._subscriber.get_data()
            if data == None:
                continue
            # Start a new file if we get
            # an data with data number 1
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

        self.log.info("Stopping Subscriber thread")
        self._subscriber.close()
        self._close_file()
        self.log.info(
            "FileWriter has written a"
            " total of %d events to %d file(s)" % (self.data_counter, self.file_counter)
        )


logprotounpack = lambda x: handlers.parseprotb2log(x)


class LogProtoSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, unpack=logprotounpack)


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
            file_prefix=file_prefix,
            ip=ip,
            port=port,
            subscriber=LogProtoSubscriber,
            writer=protobuf_io.LogWriter,
            file_ext=".prt",
            name="LogWriter",
            folder=folder,
            file_enumerator=file_enumerator,
            filesize_lim=filesize_lim,
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
            file_prefix=file_prefix,
            ip=ip,
            port=port,
            subscriber=BasicTimestampSubscriber,
            writer=protobuf_io.TimestampWriter,
            file_ext=".prt",
            name="TimestampWriter",
            folder=folder,
            file_enumerator=file_enumerator,
            filesize_lim=filesize_lim,
        )


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
            file_prefix=file_prefix,
            ip=ip,
            port=port,
            subscriber=BasicTriggerSubscriber,
            writer=protobuf_io.TriggerWriter,
            file_ext=".prt",
            name="TriggerWriter",
            folder=folder,
            file_enumerator=file_enumerator,
            filesize_lim=filesize_lim,
        )
