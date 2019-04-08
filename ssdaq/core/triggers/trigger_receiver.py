import asyncio
from ssdaq.core.receiver_server import ReceiverServer
class TriggerPacketProtocol(asyncio.Protocol):
    def __init__(self, loop, log):
        self.buffer = asyncio.Queue()
        self.loop = loop
        self.log = log.getChild("TriggerPacketProtocol")

    def connection_made(self, transport):
        self.log.info("Connected to port")
        self.transport = transport

    def datagram_received(self, data, addr):
        self.buffer.put_nowait((data, addr))


class TriggerPacketReceiver(ReceiverServer):
    def __init__(self, ip: str, port: int, publishers: list):
        super().__init__(ip, port, publishers, "TriggerPacketReceiver")
        self.trans, self.tpp = self.setup_udp(lambda: TriggerPacketProtocol(self.loop,self.log,))
        self.running = True
    async def ct_relay(self):
        while self.running:
            packet = await self.tpp.buffer.get()
            await self.publish(packet[0])


if __name__ == "__main__":
    from ssdaq.core import publishers

    trpl = TriggerPacketReceiver(
        port=2009,
        ip="0.0.0.0",
        publishers=[publishers.ZMQTCPPublisher(ip="127.0.0.101", port=5555)],
    )
    trpl.run()
