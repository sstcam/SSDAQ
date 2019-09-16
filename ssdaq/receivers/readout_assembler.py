import asyncio
import struct
import numpy as np
from datetime import datetime, timedelta
from ssdaq.data._dataimpl import slowsignal_format as dc
from ssdaq.data import SSReadout
from ssdaq.core.receiver_server import ReceiverServer
from .mon_sender import ReceiverMonSender
from collections import defaultdict

READOUT_LENGTH = (
    dc.N_TM_PIX * 2 + 2 * 8
)  # 64 2-byte channel amplitudes and 2 8-byte timestamps
packet_format = struct.Struct(">Q32HQ32H")
first_tack = struct.Struct(">Q")


class SlowSignalDataProtocol(asyncio.Protocol):
    def __init__(self, loop, log, relaxed_ip_range, mon, packet_debug_stream_file=None):
        self._buffer = asyncio.Queue()
        self.loop = loop
        self.log = log.getChild("SlowSignalDataProtocol")
        self.relaxed_ip_range = relaxed_ip_range
        self.mon = mon

    def connection_made(self, transport):
        self.log.info("Connected to port")
        self.transport = transport

    def datagram_received(self, data, addr):
        cpu_time = datetime.utcnow()
        self.mon.register_data_packet()
        if len(data) % (READOUT_LENGTH) != 0:
            self.log.warn("Got unsuported packet size, skipping packet")
            self.log.info("Bad package came from %s:%d" % tuple(data[0]))
            return

        # getting the module number from the last two digits of the ip
        ip = addr[0]
        module_nr = int(ip[-ip[::-1].find(".") :]) % 100
        # self.log.info("Got packet from module {}".format(module_nr))

        if module_nr > dc.N_TM - 1 and self.relaxed_ip_range:
            # ensure that the module number is in the allowed range
            # (mostly important for local or standalone setups simulations)
            module_nr = module_nr % dc.N_TM
            # self.log.debug('Got data from ip %s which is outsie the allowed range'%ip)
        elif module_nr > dc.N_TM - 1:
            self.log.error("Error: got packets from ip out of range:")
            self.log.error("   %s" % ip)
            self.log.error("This can be supressed if relaxed_ip_range=True")
            raise RuntimeError
        self.loop.create_task(self._buffer.put((module_nr, data, cpu_time)))


class MatchedPacket:
    def __init__(self, tm_num, data, tack, cpu_t, nreadouts):
        self.data = [None] * dc.N_TM
        self.data[tm_num] = data
        self.tm_parts = [0] * dc.N_TM
        self.tm_parts[tm_num] = 1
        self.tms = [tm_num]
        self.tack = tack
        self.cpu_t = [cpu_t]
        self.nreadouts = nreadouts

    def add_part(self, tm_num, data, cpu_t):
        self.data[tm_num] = data
        self.tm_parts[tm_num] = 1
        self.tms.append(tm_num)
        self.cpu_t.append(cpu_t)


class ReadoutAssembler(ReceiverServer):
    """
    Slow signal readout assembler. Constructs
    slow signal readouts from data packets recieved from
    Target Modules.
    """

    def __init__(
        self,
        relaxed_ip_range: bool = False,
        readout_tw: float = 0.0001 * 1e9,
        listen_ip: str = "0.0.0.0",
        listen_port: int = 2009,
        buffer_length: int = 1000,
        buffer_time: float = 10 * 1e9,
        publishers: list = None,
        packet_debug_stream_file: str = None,
    ):
        """Summary

        Args:
            relaxed_ip_range (bool, optional): Description
            readout_tw (float, optional): Description
            listen_ip (str, optional): Description
            listen_port (int, optional): Description
            buffer_length (int, optional): Description
            buffer_time (float, optional): Description
            publishers (list, optional): Description
            packet_debug_stream_file (str, optional): Description
        """
        super().__init__(listen_ip, listen_port, publishers, "ReadoutAssembler")
        self.relaxed_ip_range = relaxed_ip_range
        self.transport, self.ss_data_protocol = self.setup_udp(
            lambda: SlowSignalDataProtocol(
                self.loop,
                self.log,
                self.relaxed_ip_range,
                ReceiverMonSender("ReadoutAssembler", self.loop, self._context),
                packet_debug_stream_file=packet_debug_stream_file,
            )
        )

        # settings
        self.readout_tw = int(readout_tw)
        self.listen_addr = (listen_ip, listen_port)
        self.buffer_len = buffer_length
        self.buffer_time = buffer_time

        # counters
        self.nprocessed_packets = 0
        self.nconstructed_readouts = 0
        self.readout_count = 1
        self.packet_counter = {}
        self.readout_counter = defaultdict(lambda: 1)

        # controlers
        self.publish_readouts = True

        # buffers
        self.inter_buff = []
        self.partial_ro_buff = asyncio.queues.collections.deque(maxlen=self.buffer_len)
        self.ro_part_buff = asyncio.queues.collections.deque(maxlen=self.buffer_len)

    def cmd_reset_ro_count(self, arg):
        self.log.info("Readout count has been reset")
        self.readout_count = 1
        return b"Readout count reset"

    def cmd_set_publish_readouts(self, arg):
        if arg[0] == "false" or arg[0] == "False":
            self.publish_readouts = False
            self.log.info("Pause publishing readouts")
            return b"Paused readout publishing"
        elif arg[0] == "true" or arg[0] == "True":
            self.publish_readouts = True
            self.log.info("Pause publishing readouts")
            return b"Unpaused readout publishing"
        else:
            self.log.info(
                "Unrecognized command for command `set_publish_readouts` \n    no action taken"
            )
            return (
                "Unrecognized arg `%s` for command `set_publish_readouts` \nno action taken"
                % arg[0]
            ).encode("ascii")

    async def ct_assembler(self):
        n_packets = 0
        self.log.info("Empty socket buffer before starting readout building")
        # _ = await self.ss_data_protocol._buffer.get()
        got_packet = True
        while got_packet:
            got_packet = False
            self.log.info("Thrown away %d packets in buffer before start" % n_packets)
            try:
                while True:
                    await asyncio.wait_for(
                        self.ss_data_protocol._buffer.get(), timeout=0
                    )
                    n_packets += 1
                    got_packet = True
            except:
                pass
        self.log.info("Thrown away %d packets in buffer before start" % n_packets)
        self.log.info("Fetching first packet")

        module, data, cpu_time = await self.ss_data_protocol._buffer.get()
        tack = first_tack.unpack_from(data, 0)[0]
        nreadouts = int(len(data) / (READOUT_LENGTH))

        self.partial_ro_buff.append(
            MatchedPacket(module, data, tack, cpu_time, nreadouts)
        )
        self.log.info("Starting readout build loop")
        while True:
            module, data, cpu_time = await self.ss_data_protocol._buffer.get()
            tack = first_tack.unpack_from(data, 0)[0]
            nreadouts = int(len(data) / (READOUT_LENGTH))
            # self.log.debug('Got packet from front buffer with timestamp %f and tm id %d'%(packet[1]*1e-9,packet[0]))
            pro = self.partial_ro_buff[-1]
            dt = pro.tack - tack
            if abs(dt) < self.readout_tw:
                self.partial_ro_buff[-1].add_part(module, data, cpu_time)
            elif dt < 0:
                self.partial_ro_buff.append(
                    MatchedPacket(module, data, tack, cpu_time, nreadouts)
                )
            else:
                found = False
                for i in range(len(self.partial_ro_buff) - 1, 0, -1):
                    pro = self.partial_ro_buff[i]
                    dt = pro.timestamp - tack
                    if abs(dt) < self.readout_tw:
                        self.partial_ro_buff[-1].add_part(module, data, cpu_time)
                        found = True
                        break
                if not found:
                    self.log.warning(
                        "No matching packets found for packet with timestamp %d and tm id %d"
                        % (tack, module)
                    )
            assembling = True
            while assembling:
                if abs(
                    float(self.partial_ro_buff[-1].tack)
                    - float(self.partial_ro_buff[0].tack)
                ) > (self.buffer_time):
                    readouts = self.assemble_readouts(self.partial_ro_buff.popleft())
                    for readout in readouts:
                        await self.publish(readout.pack())
                else:
                    assembling = False
            # self.log.info("Buffer length {}".format(len(self.partial_ro_buff)))

    def assemble_readouts(self, matched):
        """Summary

        Args:
            matched (TYPE): Description

        Returns:
            TYPE: Description

        """
        # construct readout
        r_cpu_time_0 = np.min(matched.cpu_t)
        readouts = []
        tms = sorted(matched.tms)
        tack0 = matched.tack
        dts = []

        for i in range(matched.nreadouts):

            tack = first_tack.unpack_from(matched.data[tms[0]], i * (READOUT_LENGTH))[0]
            dt = tack - tack0
            dts.append(dt)
            if i > 0 and dt == 0:
                self.log.warn(
                    "Subsequent readouts with the same tack {}, {}".format(tack, i)
                )
            r_cpu_time = r_cpu_time_0 + timedelta(microseconds=dt * 1e-3)
            cpu_time_s = int(r_cpu_time.timestamp())
            cpu_time_ns = int((r_cpu_time.timestamp() - cpu_time_s) * 1e9)
            readout = SSReadout(tack, self.readout_count, cpu_time_s, cpu_time_ns)

            for tm in tms:
                tmp_data = packet_format.unpack_from(
                    matched.data[tm], i * (READOUT_LENGTH)
                )
                self.readout_counter[tm] += 1
                # put data into a temporary array of uint type
                tmp_array = np.empty(dc.N_TM_PIX, dtype=np.uint64)
                tmp_array[: dc.N_TM] = tmp_data[1 : dc.N_TM + 1]
                tmp_array[dc.N_TM :] = tmp_data[dc.N_TM + 2 :]

                # converting counts to mV
                m = tmp_array < 0x8000
                tmp_array[m] += 0x8000
                tmp_array[~m] = tmp_array[~m] & 0x7FFF
                readout.data[tm] = tmp_array * 0.03815 * 2.0

            self.nconstructed_readouts += 1
            self.readout_count += 1
            readouts.append(readout)
        return readouts


if __name__ == "__main__":
    from ssdaq import sslogger
    import logging
    import os
    from subprocess import call
    from ssdaq.core.publishers.zmq_tcp_publisher import ZMQTCPPublisher

    call(["taskset", "-cp", "0,4", "%s" % (str(os.getpid()))])
    sslogger.setLevel(logging.INFO)
    zmq_pub = ZMQTCPPublisher("127.0.0.101", 5555)
    ro_assembler = ReadoutAssembler(publishers=[zmq_pub])
    ro_assembler.run()
