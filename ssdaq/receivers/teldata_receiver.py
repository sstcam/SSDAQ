import asyncio
from ssdaq.core.receiver_server import ReceiverServer
from .mon_sender import ReceiverMonSender
from collections import deque
from ssdaq.data import TelData
from ssdaq.core.utils import get_utc_timestamp
import MySQLdb
from datetime import datetime
import os
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

            teldata = TelData()
            if os.uname().nodename == "chec1.mpi-hd.mpg.de":
                db = MySQLdb.connect(host="slntmcdb.astrivpn.com",user="ASTRI",passwd="ASTRIteam2014",db="monitoring")
                cursor = db.cursor()
                # cursor.execute("SELECT TCU_ACTUAL_DEC.timetag, TCU_ACTUAL_DEC.value, TCU_ACTUAL_RA.value  FROM TCU_ACTUAL_DEC, TCU_ACTUAL_RA WHERE timetag=(SELECT MAX(timetag) FROM TCU_ACTUAL_DEC);")
                cursor.execute("SELECT *  FROM TCU_ACTUAL_DEC WHERE timetag=(SELECT MAX(timetag) FROM TCU_ACTUAL_DEC);")
                dec = cursor.fetchall()
                cursor.execute("SELECT *  FROM TCU_ACTUAL_RA WHERE timetag=(SELECT MAX(timetag) FROM TCU_ACTUAL_RA);")
                ra = cursor.fetchall()
                sec = datetime.utcfromtimestamp(ra[0][0]/10000000-12219292800)
                teldata.time.sec = sec
                teldata.time.nsec = 0
                teldata.ra = float(ra[0][1])
                teldata.dec = float(dec[0][1])
            else:
                sec,nsec = get_utc_timestamp()
                teldata.time.sec = sec
                teldata.time.nsec = nsec
                teldata.ra = 0.322
                teldata.dec = -0.24
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
