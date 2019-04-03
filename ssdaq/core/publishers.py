class Publisher:
    def __init__(self):
        self.loop = None

    def publish(self, packet):
        raise NotImplementedError

    def set_loop(self, loop):
        self.loop = loop


class RawWriter(Publisher):
    def __init__(self, file_name):
        self.file_name = file_name
        self.file = open("file_name", "wb")

    def publish(self, packet):
        self.file.write(packet)


class ZMQTCPPublisher(Publisher):
    """ A generic zmq tcp publisher

        Publishes on a TCP/IP socket using the zmq PUB-SUB protocol.

        Args:
            ip (str):   the name (ip) interface which the readouts are published on
            port (int): the port number of the interface which the readouts are published on
        Kwargs:
            name (str): The name of this instance (usefull for logging)
            logger:     An instance of a logger to inherit from
            mode (str): The mode of publishing. Possible modes ('local','outbound', 'remote')

        The three different modes defines how the socket is setup for different use cases.

            * 'local' this is the normal use case where readouts are published on localhost
                and ip should be '127.x.x.x'
            * 'outbound' is when the readouts are published on an outbound network interface of
                the machine so that remote clients can connect to the machine to receive the readouts.
                In this case ip is the ip address of the interface on which the readouts should be published
            * 'remote' specifies that the given ip is of a remote machine to which the readouts should be sent to.


    """

    def __init__(
        self,
        ip: str,
        port: int,
        name: str = "ZMQTCPPublisher",
        logger=None,
        mode: str = "local",
    ):
        """Slow signal readout publisher
        """

        import zmq
        import logging

        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.PUB)
        con_str = "tcp://%s:" % ip + str(port)

        if mode == "local" or mode == "outbound":
            self.sock.bind(con_str)

        if mode == "outbound" or mode == "remote":
            self.sock.connect(con_str)

        if logger is None:
            self.log = logging.getLogger("ssdaq.%s" % name)
        else:
            self.log = logger.getChild(name)
        self.log.info(
            "Initialized readout publisher with a %s connection on: %s"
            % (mode, con_str)
        )

    def publish(self, packet: bytes):
        self.sock.send(packet)
