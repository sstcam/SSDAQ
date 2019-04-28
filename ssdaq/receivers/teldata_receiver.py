import asyncio
from ssdaq.core.receiver_server import ReceiverServer
from .mon_sender import ReceiverMonSender
from collections import deque
from ssdaq.data import TelData
from ssdaq.core.utils import get_utc_timestamp


class TelDataReceiver(ReceiverServer):
    def __init__(
        self, ip: str, port: int, publishers: list, name: str = "TelDataReceiver"
    ):
        self.loop = asyncio.get_event_loop()
        super().__init__(ip, port, publishers, name, self.loop)

        self.mon = ReceiverMonSender(name, self.loop, self._context)
        self._setup = True
        self.running = True

    async def ct_query_teldb(self):
        self.log.info("Starting teldb query task")
        while self.running:

            # query data base Dummy code for now
            teldata = TelData()
            sec, nsec = get_utc_timestamp()
            teldata.time.sec = sec
            teldata.time.nsec = nsec
            teldata.ra = 0.231
            teldata.dec = -0.231
            self.log.info("Created fake tel data")
            self.mon.register_data_packet()
            await self.publish(teldata.SerializeToString())
            await asyncio.sleep(15)


if __name__ == "__main__":
    from ssdaq.core import publishers

    trpl = TelDataReceiver(
        port=10001,
        ip="0.0.0.0",
        publishers=[publishers.ZMQTCPPublisher(ip="127.0.0.101", port=5559)],
    )
    trpl.run()
