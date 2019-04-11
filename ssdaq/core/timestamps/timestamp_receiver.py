import asyncio
from ssdaq.core.receiver_server import ReceiverServer

import zmq

from ssdaq.core.timestamps import CDTS_pb2
class TimestampReceiver(ReceiverServer):
    def __init__(self, ip: str, port: int, publishers: list):
        super().__init__(ip, port, publishers, "TimestampReceiver")

        self.running = True
        # The ReceiverServer already has a zmq context
        self.receiver = self._context.socket(zmq.SUB)
        self.receiver.connect("tcp://{}:{}".format(ip, port))
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, "")

    async def ct_subscribe(self):
        while self.running:
            packet = await self.receiver.recv()
            tb = CDTS_pb2.TriggerBunch()
            tb.ParseFromString(packet)
            for tm in tb.triggers:
                await self.publish(tm.SerializeToString())


if __name__ == "__main__":
    from ssdaq.core import publishers

    trpl = TriggerPacketReceiver(
        port=8307,
        ip="0.0.0.0",
        publishers=[publishers.ZMQTCPPublisher(ip="127.0.0.101", port=5555)],
    )
    trpl.run()
