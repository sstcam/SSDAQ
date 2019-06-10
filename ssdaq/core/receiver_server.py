import asyncio
import inspect
import zmq
import zmq.asyncio
from distutils.version import LooseVersion
from ssdaq import sslogger

if LooseVersion("17") > LooseVersion(zmq.__version__):
    zmq.asyncio.install()


class ReceiverServer:
    """ Base class for receivers.

        Implements some of the boilerplate code to setup a server
        that listens to either a TCP or UDP socket, publishes processed data and can
        receive commands via ipc.
        Asynchrosity is implemented using asyncio. Executing the `run()` method will,
        thus, start the event loop.

        Args:
            ip (str):           The ip address/interface to listen to
            port (int):         The port to listen to
            publishers (list):  A list of publisher instances that are cycled
                                through when `self.publish(data)` is called
            name (str):         A name for the instance (usefull for logging)
        Kwargs:
            loop (asyncio.loop):If not given an an event loop an asyncio loop will
                                retreived.
    """

    def __init__(self, ip: str, port: int, publishers: list, name: str, loop=None):
        """ The init of a ReceiverServer
        """
        self.loop = loop or asyncio.get_event_loop()
        self.log = sslogger.getChild(name)
        self._name = name
        self.publishers = publishers
        self.listen_addr = (ip, port)
        self.corrs = []
        for p in self.publishers:
            p.set_loop(self.loop)
        # setting up communications socket
        self._context = zmq.asyncio.Context()
        self._com_sock = self._context.socket(zmq.REP)
        self._com_sock.bind("ipc:///tmp/{}".format(self._name))

        self._setup = False

    def setup_stream(self, recv_protocol):
        """ Adds a TCP stream socket in the ReceiverServer eventloop.

            Args:
                recv_protocol: an asyncio.Protocol that conforms to asyncio TCP protocols
        """
        self._setup = True
        self.log.info(
            "Settting up TCP receiver socket at %s:%d" % (tuple(self.listen_addr))
        )
        listen = self.loop.create_server(
            recv_protocol, host=self.listen_addr[0], port=self.listen_addr[1]
        )
        return self.loop.run_until_complete(listen)

    def setup_udp(self, recv_protocol):
        """ Adds a UDP socket in the ReceiverServer eventloop.

            Args:
                recv_protocol: an asyncio.Protocol that conforms to asyncio Datagram protocols
        """
        self._setup = True
        self.log.info(
            "Settting up UDP receiver socket at %s:%d" % (tuple(self.listen_addr))
        )
        listen = self.loop.create_datagram_endpoint(
            recv_protocol, local_addr=self.listen_addr
        )
        return self.loop.run_until_complete(listen)

    def run(self):
        """ Starts the eventloop of the ReceiverServer (blocking)
        """
        if not self._setup:
            raise RuntimeError("No receiver socket setup")

        self.log.info("Number of publishers registered %d" % len(self.publishers))
        self._introspect()
        for c in self.corrs:
            self.loop.create_task(c)

        try:
            self.loop.run_forever()
        except Exception as e:
            self.log.error("Exception caught while running event loop: {}".format(e))

        self.loop.close()

    def _introspect(self):
        # Introspecting to find all methods that
        # handle commands
        method_list = inspect.getmembers(self, predicate=inspect.ismethod)
        self.cmds = {}
        for method in method_list:
            if method[0][:4] == "cmd_":
                self.cmds[method[0][4:]] = method[1]
            if method[0][:3] == "ct_":
                self.corrs.append(method[1]())

    async def handle_commands(self):
        """
        This is the server part of the receiver server that handles
        incomming control commands
        """
        while True:
            cmd = await self._com_sock.recv()
            self.log.info("Handling incoming command %s" % cmd.decode("ascii"))
            cmd = cmd.decode("ascii").split(" ")
            if cmd[0] in self.cmds.keys():
                reply = self.cmds[cmd[0]](cmd[1:])
            else:
                reply = b"Error, No command `%s` found." % (cmd[0])
                self.log.info("Incomming command `%s` not recognized")
            self._com_sock.send(reply)

    async def publish(self, packet: bytes):
        """ Publishes the packed processed data on the publishers
            in the publisher list of the Receiver.

            Should be called by the inheriting classes to publish data

            Args:
                packet (bytes): The data packet that should be published
        """
        tasks = []
        for pub in self.publishers:
            tasks.append(self.loop.create_task(pub.apublish(packet)))
        for task in tasks:
            await task
