from ssdaq import SSReadout

from ssdaq import SSDataWriter
from threading import Thread
from ssdaq import sslogger

from ssdaq import BasicSubscriber
import logging
import os

class SSReadoutSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(
            ip=ip, port=port, unpack=lambda data: SSReadout.from_bytes(data)
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
        filesize_lim: int = None
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
        self.filesize_lim = filesize_lim*1024**2
        self._open_file()

    def _open_file(self):
        import os
        from datetime import datetime

        self.file_readout_counter = 0
        if self.file_enumerator == "date":
            suffix = datetime.utcnow().strftime("%Y-%m-%d_%H.%M")
        elif self.file_enumerator == "order":
            suffix = "%0.3d" % self.file_counter
        else:
            suffix = ""

        self.filename = os.path.join(self.folder, self.file_prefix + suffix + ".hdf5")
        self._writer = SSDataWriter(self.filename)
        self.log.info("Opened new file, will write events to file: %s" % self.filename)

    def _close_file(self):

        from ssdaq.utils.file_size import convert_size

        self.log.info("Closing file %s" % self.filename)
        self._writer.close_file()
        self.log.info(
            "SSFileWriter has written %d events in %s bytes to file %s"
            % (
                self._writer.readout_counter,
                convert_size(os.stat(self.filename).st_size),
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
                if self.readout_counter%100 == 0 and os.stat(self.filename).st_size>self.filesize_lim:
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
