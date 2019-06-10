import struct
from collections import namedtuple
from ssdaq import sslogger
from bitarray import bitarray
import numpy as np

log = sslogger.getChild("trigger_data")
TriggerPacketHeader = struct.Struct("<H2B")


def get_SP2bptrigg_mapping():
    fMask2SPA = np.array([6, 7, 14, 12, 4, 5, 15, 13, 3, 2, 8, 11, 1, 0, 10, 9])
    fMask2SPB = np.array([9, 10, 0, 1, 11, 8, 2, 3, 13, 15, 5, 4, 12, 14, 7, 6])
    masks = [fMask2SPA, fMask2SPB]
    sel = [0, 1, 0, 1] + [1, 0] * 12 + [0, 1, 0, 1]
    m = np.zeros(512, dtype=np.uint64)
    for i, s in enumerate(sel):
        m[i * 16 : i * 16 + 16] = masks[s] + i * 16
    return m


def get_bptrigg2SP_mapping():
    fSP2MaskA = np.array([13, 12, 9, 8, 4, 5, 0, 1, 10, 15, 14, 11, 3, 7, 2, 6])
    fSP2MaskB = np.array([2, 3, 6, 7, 11, 10, 15, 14, 5, 0, 1, 4, 12, 8, 13, 9])
    masks = [fSP2MaskA, fSP2MaskB]
    sel = [0, 1, 0, 1] + [1, 0] * 12 + [0, 1, 0, 1]
    m = np.zeros(512, dtype=np.uint64)
    for i, s in enumerate(sel):
        m[i * 16 : i * 16 + 16] = masks[s] + i * 16
    return m


class TriggerPacket:
    _message_types = {}

    def __init__(self):
        pass

    @classmethod
    def register(cls, scls):
        cls._message_types[scls._mtype] = scls
        return scls

    @staticmethod
    def pack_header(mtype: int, mlength: int, magic_mark: int = 0xCAFE):
        raw_header = bytearray(TriggerPacketHeader.pack(magic_mark, mtype, mlength))
        return raw_header

    @classmethod
    def unpack(cls, data):
        magic_mark, mtype, mlen = TriggerPacketHeader.unpack(data[:4])

        if magic_mark != 0xCAFE:
            log.error(
                "Message magic marker malformed got %x instead of %x"
                % (magic_mark, 0xCAFE)
            )
            return None
        return TriggerPacket._message_types[mtype].unpack(data[4:])

    def deserialize(self, data):
        inst = TriggerPacket.unpack(data)
        self.__dict__.update(inst.__dict__)


# Old version TriggerPatternPackets
@TriggerPacket.register
class NominalTriggerPacket(TriggerPacket):
    _tail_form = struct.Struct("<3I2H")
    _mtype = 0x0

    def __init__(
        self,
        TACK: int = None,
        trigg: bitarray = None,
        uc_ev: int = None,
        uc_pps: int = None,
        uc_clock: int = None,
        type_: int = None,
    ):
        super().__init__()
        self.TACK = TACK
        self.trigg = trigg
        self.uc_ev = uc_ev
        self.uc_pps = uc_pps
        self.uc_clock = uc_clock
        self.type = type_
        self.busy = False
        self._mtype = NominalTriggerPacket._mtype

    @classmethod
    def unpack(cls, raw_packet: bytearray):
        tack = int.from_bytes(raw_packet[:8], "little")
        tbits = bitarray(0, endian="little")
        tbits.frombytes(bytes(raw_packet[8:72]))
        tail = NominalTriggerPacket._tail_form.unpack(raw_packet[72:])
        return cls(*[tack, tbits] + list(tail[:-1]))

    def pack(self):
        raw_packet = super().pack_header(self._mtype, 22)
        raw_packet.extend(self.TACK.to_bytes(8, "little"))
        raw_packet.extend(self.trigg.tobytes())
        raw_packet.extend(
            NominalTriggerPacket._tail_form.pack(
                self.uc_ev, self.uc_pps, self.uc_clock, self.type, 0
            )
        )
        return raw_packet

    def serialize(self):
        return self.pack()

    def __str__(self):
        s = ""
        s += "TACK: {}, ".format(self.TACK)
        s += "uc_ev: {}, ".format(self.uc_ev)
        s += "uc_pps: {}, ".format(self.uc_pps)
        s += "uc_clock: {}, ".format(self.uc_clock)
        s += "type: {}, \n".format(self.type)
        s += "trigg: {}".format(self.trigg)
        return s


@TriggerPacket.register
class BusyTriggerPacket(NominalTriggerPacket):
    _mtype = 0x1

    def __init__(
        self,
        TACK: int = None,
        trigg: bitarray = None,
        uc_ev: int = None,
        uc_pps: int = None,
        uc_clock: int = None,
        type_: int = None,
    ):
        super().__init__(TACK, trigg, uc_ev, uc_pps, uc_clock, type_)
        self.busy = True
        self._mtype = BusyTriggerPacket._mtype


# End of old version of Trigger pattern packets
# New version Trigger pattern packets
of = 2


@TriggerPacket.register
class NominalTriggerPacketV2(TriggerPacket):
    _mtype = 0x2 - of
    _head_form = struct.Struct("<QB512H")
    _tail_form = struct.Struct("<3I2H")

    def __init__(
        self,
        TACK: int = 0,
        trigg_phase: int = 0,
        trigg_phases: np.ndarray = np.zeros(512, dtype=np.uint16),
        trigg_union: bitarray = bitarray("0" * 512),
        uc_ev: int = 1,
        uc_pps: int = 1,
        uc_clock: int = 1,
        type_: int = 0,
    ):
        super().__init__()
        self._TACK = TACK
        self._trigg_phase = trigg_phase
        self._uc_ev = uc_ev
        self._uc_pps = uc_pps
        self._uc_clock = uc_clock
        self._type = type_
        self._busy = False
        self._mtype = NominalTriggerPacketV2._mtype
        self._trigger_phases = np.array(trigg_phases, dtype=np.uint16)
        self._trigg = None
        self._trigg_union = trigg_union

    def _compute_trigg(self):
        trigg_phase_number = self.trigg_phase
        print(trigg_phase_number)
        self._trigg = (trigg_phase_number == self._trigger_phases).astype(np.uint16)
        return self._trigg

    @property
    def busy(self):
        return self._busy

    @property
    def TACK(self):
        return self._TACK

    @property
    def trigg_phase(self):
        return self._trigg_phase

    @property
    def uc_ev(self):
        return self._uc_ev

    @property
    def uc_pps(self):
        return self._uc_pps

    @property
    def uc_clock(self):
        return self._uc_clock

    @property
    def type(self):
        return self._type

    @property
    def mtype(self):
        return self._mtype

    @property
    def trigg(self):
        if self._trigg is None:
            self._compute_trigg()
        return self._trigg

    @property
    def trigg_union(self):
        return np.frombuffer(self._trigg_union.unpack(), dtype=bool)

    @classmethod
    def unpack(cls, raw_packet: bytearray):
        data_part1 = NominalTriggerPacketV2._head_form.unpack(
            raw_packet[: -int(512 / 8) - NominalTriggerPacketV2._tail_form.size]
        )  # int.from_bytes(raw_packet[:8], "little")
        tack, phase = data_part1[0], data_part1[1]

        tbits = bitarray(0, endian="little")
        tbits.frombytes(
            bytes(
                raw_packet[
                    NominalTriggerPacketV2._head_form.size : -NominalTriggerPacketV2._tail_form.size
                ]
            )
        )
        tail = NominalTriggerPacket._tail_form.unpack(
            raw_packet[-NominalTriggerPacketV2._tail_form.size :]
        )
        return cls(
            *[tack, phase, np.array(data_part1[2:], dtype=np.uint16), tbits]
            + list(tail[:-1])
        )

    def pack(self):
        raw_packet = super().pack_header(self._mtype, 22)
        raw_packet.extend(self.TACK.to_bytes(8, "little"))
        raw_packet.extend(self.trigg_phase.to_bytes(1, "little"))
        raw_packet.extend(self._trigger_phases.tobytes())
        raw_packet.extend(self._trigg_union.tobytes())
        raw_packet.extend(
            NominalTriggerPacket._tail_form.pack(
                self.uc_ev, self.uc_pps, self.uc_clock, self.type, 0
            )
        )
        return raw_packet

    def serialize(self):
        return self.pack()

    def __str__(self):
        s = "<{}>   ".format(self.__class__.__name__)
        s += "TACK: {}, ".format(self.TACK)
        s += "trigger_phase: {}, ".format(int(np.log2(self.trigg_phase + 1)))
        s += "uc_ev: {}, ".format(self.uc_ev)
        s += "uc_pps: {}, ".format(self.uc_pps)
        s += "uc_clock: {}, ".format(self.uc_clock)
        s += "type: {}, \n".format(self.type)
        s += "trigg: {}".format(self.trigg)

        return s


@TriggerPacket.register
class BusyTriggerPacketV2(NominalTriggerPacketV2):
    _mtype = 0x3 - of

    def __init__(
        self,
        TACK: int = 0,
        trigg_phase: int = 0,
        trigg_phases: np.ndarray = np.zeros(512, dtype=np.uint16),
        trigg_union: bitarray = bitarray("0" * 512),
        uc_ev: int = 1,
        uc_pps: int = 1,
        uc_clock: int = 1,
        type_: int = 0,
    ):
        super().__init__(
            TACK, trigg_phase, trigg_phases, trigg_union, uc_ev, uc_pps, uc_clock, type_
        )
        self._busy = False
        self._mtype = BusyTriggerPacketV2._mtype
