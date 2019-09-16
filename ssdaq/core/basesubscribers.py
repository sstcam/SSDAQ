""" This module defines the BaseSubscribers for receiving data from Recievers
"""
from threading import Thread
import zmq
import zmq.asyncio
from queue import Queue
import logging
from ssdaq import sslogger
import asyncio
from .io import BaseFileWriter


class BasicSubscriber(Thread):
    """The base class to subscribe to a published data stream from a reciver.
        Data are retrived by the `get_data()` method once the listener has been started by the
        `start()` method.

    Attributes:
        log (logging.logger): logging instance

    """

    _id_counter = 0

    def __init__(
        self,
        ip: str,
        port: int,
        unpack=None,
        logger: logging.Logger = None,
        zmqcontext=None,
    ):
        """ The init of a BasicSubscriber

                Args:
                    ip (str): The ip address where the datas are published (can be local or remote)
                    port (int): The port number at which the datas are published
                    unpack (None, optional): A callable which takes the received data packet as input
                                        and returns an unpacked object. If not given the packed data
                                        object is put in the subscribed buffer.
                    logger (logging.Logger, optional): Optionally provide a logger instance
                    zmqcontext (None, optional): Description
        """
        Thread.__init__(self)
        BasicSubscriber._id_counter += 1
        self.log = logger or logging.getLogger(
            "ssdaq.BasicSubscriber%d" % BasicSubscriber._id_counter
        )

        self._context = zmqcontext or zmq.Context()
        self._sock = self._context.socket(zmq.SUB)
        self._sock.setsockopt(zmq.SUBSCRIBE, b"")
        con_str = "tcp://%s:%s" % (ip, port)
        if "0.0.0.0" == ip:
            self._sock.bind(con_str)
        else:
            self._sock.connect(con_str)
        self.log.info("Connected to : %s" % con_str)
        self._running = False
        self._data_buffer = Queue()

        self._id_counter = BasicSubscriber._id_counter
        self._inproc_sock_name = "SSdataListener%d" % (self._id_counter)
        self._close_sock = self._context.socket(zmq.PAIR)
        self._close_sock.bind("inproc://" + self._inproc_sock_name)
        self._unpack = (lambda x: x) if unpack is None else unpack

    def close(self, hard=True):
        """Closes subscriber so no more data is put in the buffer

        args:
            hard (bool): If set to true the buffer will be emptied and
                        any data still in the buffer will be lost.
        """

        if self._running:
            self.log.debug("Sending close message to listener thread")
            self._close_sock.send(b"close")
            self._running = False

        if hard:
            self.log.info("Emptying data buffer")
            # Empty the buffer after closing the recv thread
            while not self._data_buffer.empty():
                self._data_buffer.get()
                self._data_buffer.task_done()
            self._data_buffer.join()

    def get_data(self, **kwargs):
        """Returns unpacked data from the published data stream.
        By default a blocking call. See python Queue docs.

        Args:
            **kwargs: See queue.Queue docs

        Returns:
            bytes: bytes data representing the published object

        """
        data = self._data_buffer.get(**kwargs)
        self._data_buffer.task_done()
        return data

    def empty(self):
        """Returns true if the subscriber buffer is empty

        Returns:
            bool: True if empty
        """
        return self._data_buffer.empty()

    def run(self):
        """This is the main method of the listener - the listening thread.
        """
        self.log.info("Starting listener")
        recv_close = self._context.socket(zmq.PAIR)
        con_str = "inproc://" + self._inproc_sock_name
        recv_close.connect(con_str)
        self._running = True
        self.log.debug("Connecting close socket to %s" % con_str)
        poller = zmq.Poller()
        poller.register(self._sock, zmq.POLLIN)
        poller.register(recv_close, zmq.POLLIN)

        while self._running:

            socks = dict(poller.poll())

            if self._sock in socks:
                data = self._sock.recv()
                self._data_buffer.put(self._unpack(data))
            else:
                self.log.info("Stopping")
                self._data_buffer.put(None)
                break
        self._running = False


class WriterSubscriber(Thread, BaseFileWriter):
    """
    Attributes:
        log (TYPE): Description
        stopping (bool): Description

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
        self._running = False
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
            self._running = False
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
        self._running = True
        while self._running:

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
    The ``AsyncSubscriber`` provides the same basic functionality as the ``BasicSubscriber``, however,
    it is intended to work in an asynchronous enviroment using ``asyncio``.

    The ``get_data`` and ``close`` methods are therefore coroutines which should be called in an event loop.
    An event loop can be passed to the subscriber but if none is passed then it tries to get one itself.
    Further a ``passoff_callback`` function can be passed that overrides the default behavior of putting
    the received unpacked data in a queue which accessed with ``get_data``.

    Attributes:
        log (logging.logger): logger instance

    """

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
            name (str, optional): The name of the subscriber (used in logging)


        """
        logger = logger or sslogger
        name = name or __class__.__name__
        self.log = logger.getChild(name)
        self._context = zmqcontext or zmq.asyncio.Context()
        self._sock = self._context.socket(zmq.SUB)
        self._sock.setsockopt(zmq.SUBSCRIBE, b"")
        con_str = "tcp://%s:%s" % (ip, port)
        if "0.0.0.0" == ip:
            self._sock.bind(con_str)
        else:
            self._sock.connect(con_str)
        self.log.info("Connected to : %s" % con_str)
        self._running = False
        self._data_buffer = asyncio.Queue()
        self._loop = loop or asyncio.get_event_loop()
        self._running = True
        self._unpack = (lambda x: x) if unpack is None else unpack
        self._task = self._loop.create_task(self.receive())
        self._passoff_callback = passoff_callback or (
            lambda x: self._loop.create_task(self._data_buffer.put(x))
        )

    async def receive(self):
        """**(Coroutine)** The main method of the subscriber where the data is received.
        This method is placed in the event loop as a task at initialization.

        """
        self.log.info("Start subscription")
        while self._running:
            data = None
            try:
                data = self._unpack(await self._sock.recv())
            except asyncio.CancelledError:
                self.log.info("Subscription stopped")
                return
            except Exception as e:
                self.log.warning("An error ocurred while unpacking data {}".format(e))

            self._passoff_callback(data)
        self.log.info("Subscription stopped")

    async def get_data(self):
        """**(Coroutine)** Get data from the subscriber buffer.

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
        """**(Coroutine)** Closes subscriber so no more data is put in the buffer

        args:
            hard (bool): If set to true the buffer will be emptied and
                        any data still in the buffer will be lost.
        """
        self._running = False

        if not self._task.cancelled():
            self._sock.close()
            self._task.cancel()
        await self._task


class AsyncWriterSubscriber(BaseFileWriter):
    """
        An asynchronous writer subscriber

        This class subscribes to a zmq stream and writes the received data
        to a file using an appropriate writer.

    Attributes:
        log (logging.logger): logger instance
        loop (asyncio.eventloop): eventloop
        running (bool): True if receieving and writing
        stopping (bool): True after receiveing stop command
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
        """ Summary

        Args:
            file_prefix (str): Description
            ip (str): Description
            port (int): Description
            subscriber (AsyncSubscriber): Description
            writer (TYPE): Description
            file_ext (str): Description
            name (str): Description
            folder (str, optional): Description
            file_enumerator (str, optional): Description
            filesize_lim (int, optional): Description
            loop (None, optional): Description
        """
        self.log = sslogger.getChild(name)
        super().__init__(
            file_prefix=file_prefix,
            writer=writer,
            folder=folder,
            file_enumerator=file_enumerator,
            filesize_lim=filesize_lim,
            file_ext=file_ext,
        )
        self._loop = loop or asyncio.get_event_loop()
        self._subscriber = subscriber(
            ip=ip, port=port, loop=self._loop, logger=self.log, name="mainsub"
        )
        self._running = False
        self.stopping = False
        self._task = self._loop.create_task(self.run())

    async def run(self):
        self.log.info("Starting writer")
        self._running = True
        while self._running:
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
            self._running = False
            self.log.info("Hard stop. Dropping buffers!!")
        # set stopping flag to true
        self.stopping = True
        # close subscriber
        self.log.info("Stopping Subscriber")
        await self._subscriber.close(hard=False)

        if self._subscriber.empty():
            if not self._task.cancelled():
                self.log.info("Cancelling")
                self._task.cancel()
        await self._task
        # Closing the BaseFilewriter to close the
        # filehandle and get a nice summary log message
        super().close()
