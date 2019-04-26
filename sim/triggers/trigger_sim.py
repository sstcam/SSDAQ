import socket
import os
import numpy as np
import time
from datetime import datetime

import struct
import asyncio
import zmq
import zmq.asyncio
from queue import Queue
import inspect
from ssdaq.data import trigger_format as data
import bitarray


class TMMessage(object):
    def __init__(self, name=None, ip=None):
        self.name = name
        self.ip = ip

    def encode(self, status, msg):
        import pickle

        if self.name != None and self.ip != None:
            return pickle.dumps(
                {"name": self.name, "ip": self.ip, "status": status, "msg": msg},
                protocol=3,
            )
        else:
            raise RuntimeError

    @staticmethod
    def decode(msg):
        return pickle.loads(msg)


class TriggerPacketGenerator(object):
    def __init__(
        self, send_port, server_port, host_ip="127.0.0.1", my_ip="127.0.0.1", tm_id=1
    ):
        self.corrs = [self.handle_commands(), self.send_triggers_data(), self.sync()]
        self.loop = asyncio.get_event_loop()
        self.futures = []

        self.send_port = send_port
        self.host_ip = host_ip
        self.my_ip = my_ip
        self.id = tm_id
        self.msg = TMMessage(name="TM:%d" % self.id, ip=self.my_ip)

        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host_address = (self.host_ip, send_port)
        self.npackets = 0

        self.send_triggers_datae = asyncio.Event()
        self.send_triggers_datae.set()  # by default the simulation should be running
        self.sync_ss_data = asyncio.Event()
        self.sync_ss_data.set()
        self.server_port = server_port
        self.context = zmq.asyncio.Context()
        self.com_sock = self.context.socket(zmq.REP)
        self.com_sock.bind("tcp://%s:%s" % ("0.0.0.0", self.server_port))

        method_list = inspect.getmembers(self, predicate=inspect.ismethod)
        self.cmds = {}
        for method in method_list:
            if method[0][:4] == "cmd_":
                self.cmds[method[0][4:]] = method[1]

    def cmd_available_cmds(self, arg):
        return self.msg.encode("OK", list(self.cmds.keys()))

    def cmd_ping(self, arg):
        return self.msg.encode("OK", "Ping!")

    def cmd_send_triggers_data(self, arg):
        if len(arg) == 1:
            arg = arg[0]
        else:
            return self.msg.encode("Error", "Wrong number of arguments")
        if arg == "True" or arg == "true":
            self.sending_triggers_data = True
        elif arg == "False" or arg == "false":
            self.sending_triggers_data = False
        else:
            return self.msg.encode("Error", "Argument `%s` not recognized as boolean")

        if self.sending_triggers_data:
            self.send_triggers_datae.set()
        else:
            self.send_triggers_datae.clear()

        return self.msg.encode(
            "OK", "send_triggers_data set to: %s" % self.sending_triggers_data
        )

    def cmd_is_sending_triggers_data(self, arg):
        return self.msg.encode("OK", self.sending_triggers_data)

    def cmd_change_rate(self, arg):
        # self.logger.debug('arg %s'%arg)
        if len(arg) == 1:
            self.dt = 1 / float(arg[0])
            return self.msg.encode("OK", "New rate set to %f Hz" % (float(arg[0])))
        else:
            return self.msg.encode("Error", "Wrong number of arguments")

    def cmd_get_rate(self, arg):
        return self.msg.encode("OK", 1.0 / self.dt)

    def cmd_get_npackets_sent(self, arg):
        return self.msg.encode("OK", self.npackets)

    def run(self):
        for c in self.corrs:
            self.futures.append(self.loop.create_task(c))
        try:
            self.loop.run_forever()
        except:
            pass
        self.loop.close()

    async def handle_commands(self):
        """
        This is the server part of the simulation that handles
        incomming commands to control the simulation
        """
        while True:
            cmd = await self.com_sock.recv()
            # self.logger.info('Handling incoming command %s'%cmd.decode('ascii'))
            cmd = cmd.decode("ascii").split(" ")
            if cmd[0] in self.cmds.keys():
                reply = self.cmds[cmd[0]](cmd[1:])
            else:
                reply = self.msg.encode("Error", "No command `%s` found." % (cmd[0]))
                # self.logger.info('Incomming command `%s` not recognized')
            self.com_sock.send(reply)

    async def sync(self):
        while True:

            t = datetime.utcnow()
            sleeptime = 1.0 - t.microsecond / 1000000.0
            await asyncio.sleep(sleeptime)
            self.sync_ss_data.set()

    async def send_triggers_data(self):
        header = data.TriggerPacketData.pack_header(0, 22)
        tack = 0
        while True:
            # packet = bytearray(header)
            trp = bitarray.bitarray(0, endian="little")
            i = 2 ** 512 - 1
            trp.frombytes(i.to_bytes(64, "little"))

            # packet.extend()
            packet = bytearray(
                data.NominalTriggerDataEncode.pack(tack, trp, 2, 3, 4, 0)
            )
            tack += 1
            # print("Sending packet")
            # print(packet)
            self.udp_sock.sendto(packet, self.host_address)
            time.sleep(0.00001)


if __name__ == "__main__":

    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="A TARGET-C module simulator for slow signal data. For localhost simulation use defaults.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-d",
        "--data-port",
        type=int,
        default=8307,
        dest="data_port",
        help="Slow signal data port",
    )

    parser.add_argument(
        "-c",
        "--com-port",
        type=int,
        default=30001,
        dest="com_port",
        help="Communications port",
    )
    parser.add_argument(
        "-i",
        "--ip",
        type=str,
        default="127.0.0.1",
        dest="host_ip",
        help="IP address of the host. For local host it is 127.0.0.1",
    )
    parser.add_argument(
        "-m",
        "--my-ip",
        dest="my_ip",
        type=str,
        default="127.0.0.1",
        help="IP address of the TM. For local host it is 127.0.0.1",
    )
    parser.add_argument(
        "-t", "--tm-id", dest="tm_id", type=int, default=1, help="Target module id"
    )

    args = parser.parse_args()

    triggsim = TriggerPacketGenerator(
        args.data_port,
        str(args.com_port),
        args.host_ip,
        my_ip=args.my_ip,
        tm_id=args.tm_id,
    )
    triggsim.run()
