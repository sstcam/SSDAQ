import asyncio
import pickle
import struct
import logging
import logging.handlers
from signal import SIGTERM, SIGQUIT, SIGINT


class LogReceiverProtocol(asyncio.Protocol):
    def __init__(self, server, loop, log):
        self._buffer = asyncio.Queue()
        self.server = server
        self.loop = loop
        self.log = log.getChild("LogReceiverProtocol")

    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info("peername")
        self.log.info("Connection from {}".format(self.peername))

    def data_received(self, data):
        # print(struct.unpack('>L',data[:4]))
        record = logging.makeLogRecord(pickle.loads(data[4:]))
        self.loop.create_task(self.server.receive_log(record))

    def connection_lost(self, exc):
        self.log.info("Lost connection of {}".format(self.peername))
        self.transport.close()


from ssdaq.core.receiver_server import ReceiverServer


class LoggReceiver(ReceiverServer):
    def __init__(self, ip: str, port: int, publishers: list, name: str = "LogReceiver"):
        self.loop = asyncio.get_event_loop()
        super().__init__(ip, port, publishers, name, self.loop)
        self.receiver = self.setup_stream(
            lambda: LogReceiverProtocol(self, self.loop, self.log)
        )

    async def receive_log(self, record):
        import pickle

        await self.publish(pickle.dumps(record))


if __name__ == "__main__":
    from ssdaq.core import publishers

    trpl = LoggReceiver(
        port=10001,
        ip="0.0.0.0",
        publishers=[publishers.ZMQTCPPublisher(ip="127.0.0.101", port=5559)],
    )
    trpl.run()
