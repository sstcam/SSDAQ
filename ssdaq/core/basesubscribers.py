from threading import Thread
import zmq
import zmq.asyncio
from queue import Queue
import logging
from .utils import get_si_prefix
from ssdaq import sslogger
import asyncio
from .io import BaseFileWriter


class BasicSubscriber(Thread):
    """ The base class to subscribe to a published data stream from a reciver.
        Data are retrived by the `get_data()` method once the listener has been started by the
        `start()` method


    """

    id_counter = 0

    def __init__(self, ip: str, port: int, unpack=None, logger: logging.Logger = None):
        """ The init of a BasicSubscriber

            Args:
                ip (str):   The ip address where the datas are published (can be local or remote)
                port (int): The port number at which the datas are published

            Kwargs:
                unpack (callable): A callable which takes the received data packet as input
                                    and returns an unpacked object. If not given the packed data
                                    object is put in the subscribed buffer.
                logger:     Optionally provide a logger instance
        """
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

    def close(self, hard=True):
        """ Closes subscriber so no more data is put in the buffer
            args:
                hard (bool): If set to true the buffer will be emptied and
                            any data still in the buffer will be lost.
        """

        if self.running:
            self.log.debug("Sending close message to listener thread")
            self.close_sock.send(b"close")
            self.running = False

        if hard:
            self.log.info("Emptying data buffer")
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

    def empty(self):
        """ Returns true if the subscriber buffer is empty
        """
        return self._data_buffer.empty()

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


class WriterSubscriber(Thread, BaseFileWriter):
    """
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
        """Summary

        Args:
            file_prefix (str): Description
            ip (str): Description
            port (int): Description
            subscriber (BasicSubscriber): Description
            writer (TYPE): Description
            file_ext (str): Description
            name (str): Description
            folder (str, optional): Description
            file_enumerator (str, optional): Description
            filesize_lim (int, optional): Description
        """
        self.log = sslogger.getChild(name)
        BaseFileWriter.__init__(
            self,
            file_prefix=file_prefix,
            writer=writer,
            folder=folder,
            file_enumerator=file_enumerator,
            filesize_lim=filesize_lim,
            file_ext=file_ext,
        )
        Thread.__init__(self)

        self._subscriber = subscriber(
            logger=self.log.getChild("Subscriber"), ip=ip, port=port
        )
        self.running = False
        self.stopping = False

    def close(self, hard: bool = False, non_block: bool = False):
        """ Stops the writer by closing the subscriber

            args:
                hard (bool): If set to true the subscriber
                             buffer will be dropped and the file
                             will be immediately closed. Any data still
                             in the subscriber buffer will be lost.
                non_block (bool): If set to true will not block
        """
        if hard:
            self.running = False
        # set stopping flag to true
        self.stopping = True
        # close subscriber
        self.log.info("Stopping Subscriber thread")
        self._subscriber.close(hard=hard)
        if not non_block:
            self.join()
        BaseFileWriter.close(self)

    def run(self):
        self.log.info("Starting writer thread")
        self._subscriber.start()
        self.running = True
        while self.running:

            data = self._subscriber.get_data()
            if data == None:
                if self.stopping and self._subscriber.empty():
                    break
                continue
            self.write(data)


from distutils.version import LooseVersion

if LooseVersion("17") > LooseVersion(zmq.__version__):
    zmq.asyncio.install()


class AsyncSubscriber:
    """

    """

    id_counter = 0

    def __init__(
        self,
        ip: str,
        port: int,
        unpack=None,
        logger: logging.Logger = None,
        zmqcontext=None,
        loop=None,
        passoff_callback=None,
        name: str = None,
    ):
        """The init of an AsyncSubscriber

        Args:
            ip (str): The ip address where the datas are published (can be local or remote)
            port (int): The port number at which the datas are published
            unpack (None, optional): A callable which takes the received data packet as input
                                and returns an unpacked object. If not given the packed data
                                object is put in the subscribed buffer.
            logger (logging.Logger, optional): Optionally provide a logger instance
            zmqcontext (None, optional): zmq context
            loop (None, optional): an asyncio event loop
            passoff_callback (None, optional): An optional callback for overriding the default
                                            buffer. Note: if this is used then ``get_data()``
                                            will always be empty.
            name (str, optional): Description


        """
        logger = logger or sslogger
        name = name or __class__.__name__
        self.log = logger.getChild(name)
        self.context = zmqcontext or zmq.asyncio.Context()
        self.sock = self.context.socket(zmq.SUB)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        con_str = "tcp://%s:%s" % (ip, port)
        if "0.0.0.0" == ip:
            self.sock.bind(con_str)
        else:
            self.sock.connect(con_str)
        self.log.info("Connected to : %s" % con_str)
        self.running = False
        self._data_buffer = asyncio.Queue()
        self.loop = loop or asyncio.get_event_loop()
        self.running = True
        self.unpack = (lambda x: x) if unpack is None else unpack
        self.task = self.loop.create_task(self.receive())
        self.passoff_callback = passoff_callback or (
            lambda x: self.loop.create_task(self._data_buffer.put(x))
        )

    async def receive(self):
        self.log.info("Start subscription")
        while self.running:
            data = None
            try:
                data = self.unpack(await self.sock.recv())
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.log.warning("An error ocurred while unpacking data {}".format(e))

            self.passoff_callback(data)

    async def get_data(self):
        """Get data from the subscriber buffer.

        Returns:
            data: data object
        """
        data = await self._data_buffer.get()
        self._data_buffer.task_done()
        return data

    def empty(self):
        """ Returns true if the subscriber buffer is empty
        """
        return self._data_buffer.empty()

    async def close(self, hard=True):
        """Closes subscriber so no more data is put in the buffer

        args:
            hard (bool): If set to true the buffer will be emptied and
                        any data still in the buffer will be lost.
        """
        self.running = False

        if not self.task.cancelled():
            self.sock.close()
            self.task.cancel()
        await self.task


class AsyncWriterSubscriber(BaseFileWriter):
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
        subscriber: AsyncSubscriber,
        writer,
        file_ext: str,
        name: str,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
        loop=None,
    ):
        self.log = sslogger.getChild(name)
        super().__init__(
            file_prefix=file_prefix,
            writer=writer,
            folder=folder,
            file_enumerator=file_enumerator,
            filesize_lim=filesize_lim,
            file_ext=file_ext,
        )
        self.loop = loop or asyncio.get_event_loop()
        self._subscriber = subscriber(
            ip=ip, port=port, loop=self.loop, logger=self.log, name="mainsub"
        )
        self.running = False
        self.stopping = False
        self.task = self.loop.create_task(self.run())

    async def run(self):
        self.log.info("Starting writer")
        self.running = True
        while self.running:
            if self.stopping and self._subscriber.empty():
                break
            try:
                data = await self._subscriber.get_data()
            except asyncio.CancelledError:
                continue
            except Exception as e:
                self.log.error("Exception: {}, occured while retreiving data".format(e))
                continue
            if data == None:
                continue

            self.write(data)

    async def close(self, hard: bool = False):
        """Stops the writer by closing the subscriber.

        args:
            hard (bool, optional): If set to true the subscriber
                         buffer will be dropped and the file
                         will be immediately closed. Any data still
                         in the subscriber buffer will be lost.
        """
        if hard:
            self.running = False
            self.log.info("Hard stop. Dropping buffers!!")
        # set stopping flag to true
        self.stopping = True
        # close subscriber
        self.log.info("Stopping Subscriber")
        await self._subscriber.close(hard=False)

        if self._subscriber.empty():
            if not self.task.cancelled():
                self.log.info("Cancelling")
                self.task.cancel()
        await self.task
        # Closing the BaseFilewriter to close the
        # filehandle and get a nice summary log message
        super().close()
