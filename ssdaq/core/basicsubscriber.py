from threading import Thread
import zmq
from queue import Queue
import logging
from .utils import get_si_prefix
from ssdaq import sslogger
from datetime import datetime
import os


class BasicSubscriber(Thread):
    """ A convinience class to subscribe to a published data stream from a reciver.
        Data are retrived by the `get_data()` method once the listener has been started by the
        `start()` method

        Args:
            ip (str):   The ip address where the datas are published (can be local or remote)
            port (int): The port number at which the datas are published
        Kwargs:
            logger:     Optionally provide a logger instance
    """

    id_counter = 0

    def __init__(self, ip: str, port: int, unpack=None, logger: logging.Logger = None):
        Thread.__init__(self)
        BasicSubscriber.id_counter += 1
        self.log = logger or logging.getLogger(
            "ssdaq.BasicSubscriber%d" % BasicSubscriber.id_counter
        )

        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.SUB)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        con_str = "tcp://%s:%s" % (ip, port)
        if "0.0.0.0" == ip:
            self.sock.bind(con_str)
        else:
            self.sock.connect(con_str)
        self.log.info("Connected to : %s" % con_str)
        self.running = False
        self._data_buffer = Queue()

        self.id_counter = BasicSubscriber.id_counter
        self.inproc_sock_name = "SSdataListener%d" % (self.id_counter)
        self.close_sock = self.context.socket(zmq.PAIR)
        self.close_sock.bind("inproc://" + self.inproc_sock_name)
        self.unpack = (lambda x: x) if unpack is None else unpack

    def close(self):
        """ Closes listener thread and empties the data buffer to unblock the
            the get_data method
        """

        if self.running:
            self.log.debug("Sending close message to listener thread")
            self.close_sock.send(b"close")
        self.log.debug("Emptying data buffer")
        # Empty the buffer after closing the recv thread
        while not self._data_buffer.empty():
            self._data_buffer.get()
            self._data_buffer.task_done()
        self._data_buffer.join()

    def get_data(self, **kwargs):
        """ Returns unpacked data from the published data stream.
            By default a blocking call. See python Queue docs.

            Kwargs:
                See queue.Queue docs

        """
        data = self._data_buffer.get(**kwargs)
        self._data_buffer.task_done()
        return data

    def run(self):
        """ This is the main method of the listener
        """
        self.log.info("Starting listener")
        recv_close = self.context.socket(zmq.PAIR)
        con_str = "inproc://" + self.inproc_sock_name
        recv_close.connect(con_str)
        self.running = True
        self.log.debug("Connecting close socket to %s" % con_str)
        poller = zmq.Poller()
        poller.register(self.sock, zmq.POLLIN)
        poller.register(recv_close, zmq.POLLIN)

        while self.running:

            socks = dict(poller.poll())

            if self.sock in socks:
                data = self.sock.recv()
                self._data_buffer.put(self.unpack(data))
            else:
                self.log.info("Stopping")
                self._data_buffer.put(None)
                break
        self.running = False


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
        self.filesize_lim = ((filesize_lim or 0) * 1024 ** 2) or None
        self._writercls = writer
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
            "SSFileWriter has written %d events in %g%sB to file %s"
            % (
                self._writer.data_counter,
                *get_si_prefix(os.stat(self.filename).st_size),
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
