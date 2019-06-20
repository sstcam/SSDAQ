from ssdaq.data import MonitorData
import datetime
import os
import zmq
import asyncio


class ReceiverMonSender:
    def __init__(self, name, loop, zmqcontext):
        """Summary

        Args:
            name (TYPE): Description
            loop (TYPE): Description
            zmqcontext (TYPE): Description
        """
        # monitoring socket
        self._context = zmqcontext
        self._monitor_sock = self._context.socket(zmq.PUSH)
        self._monitor_sock.connect("tcp://127.0.0.101:10002")
        self.total_data_counter = 0
        self.current_data_counter = 0
        self.got_data = False
        self.data_timeout = None
        self.mon_wait = 1.0
        self.name = name
        self.past = None
        loop.create_task(self.sendmon())
        self.loop = loop

    def register_data_packet(self):
        """Summary
        """
        self.total_data_counter += 1
        self.current_data_counter += 1
        self.got_data = True

    def _compute_rates(self):
        """Summary

        Returns:
            TYPE: Description
        """
        now = datetime.datetime.now().timestamp()

        if self.past is None:
            self.past = now
            self.current_data_counter = 0
            return
        dt = now - self.past
        self.past = now
        rate = self.current_data_counter / dt
        self.current_data_counter = 0

        return rate

    async def sendmon(self):
        """Summary
        """
        while True:
            await asyncio.sleep(self.mon_wait)

            mdata = MonitorData()
            # constructing timestamp
            tstamp = datetime.datetime.utcnow().timestamp()
            mdata.time.sec = int(tstamp)
            mdata.time.nsec = int((tstamp - mdata.time.sec) * 1e9)
            # Constructing monitoring message
            mdata.reciver.pid = os.getpid()
            mdata.reciver.name = self.name
            rate = self._compute_rates()
            if rate is None:
                continue
            mdata.reciver.data_rate = rate
            mdata.reciver.recv_data = self.got_data
            self.got_data = False
            # Putting it into a monitor data message

            self._monitor_sock.send(mdata.SerializeToString())
