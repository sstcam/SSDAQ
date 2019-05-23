import struct
from collections import namedtuple
from ssdaq import sslogger
from bitarray import bitarray

log = sslogger.getChild("trigger_data")

TriggerPacketHeader = struct.Struct("<H2B")

class TriggerPacket:
    _message_types ={}
    def __init__(self,mtype=None,mlen=None):
        self.mtype = mtype
        self.mlen = mlen

    @classmethod
    def register(cls, scls,):
        cls._message_types[scls._mtype] = scls
        return scls

    @staticmethod
    def pack_header(mtype: int, mlength: int, magic_mark: int = 0xCAFE):
        raw_header = bytearray(TriggerPacketHeader.pack(magic_mark, mtype, mlength))
        return raw_header

    @classmethod
    def unpack(cls,data):
        magic_mark, mtype, mlen = TriggerPacketHeader.unpack(data[:4])

        if magic_mark != 0xCAFE:
            log.error(
                "Message magic marker malformed got %x instead of %x"
                % (magic_mark, 0xCAFE)
            )
            return None
        return TriggerPacket._message_types[mtype].unpack(data[4:])

    def deserialize(self,data):
        inst = TriggerPacket.unpack(data)
        self.__dict__.update(inst.__dict__)

@TriggerPacket.register
class NominalTriggerPacket(TriggerPacket):
    _tail_form = struct.Struct("<3I2H")
    _mtype = 0x1
    def __init__(self,
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

    @classmethod
    def unpack(cls,raw_packet: bytearray):
        tack = int.from_bytes(raw_packet[:8], "little")
        tbits = bitarray(0, endian="little")
        tbits.frombytes(bytes(raw_packet[8:72]))
        tail = NominalTriggerPacket._tail_form.unpack(raw_packet[72:])
        return cls(*[tack, tbits] + list(tail[:-1]))

    def pack(self):
        raw_packet = super().pack_header(0x1, 22)
        raw_packet.extend(self.TACK.to_bytes(8, "little"))
        raw_packet.extend(self.trigg.tobytes())
        raw_packet.extend(
            NominalTriggerPacket._tail_form.pack(self.uc_ev, self.uc_pps, self.uc_clock, self.type, 0)
        )
        return raw_packet

    def serialize(self):
        return self.pack()

    def __str__(self):
        s = ""
        s +="TACK: {}, ".format(self.TACK)
        s +="uc_ev: {}, ".format(self.uc_ev)
        s +="uc_pps: {}, ".format(self.uc_pps)
        s +="uc_clock: {}, ".format(self.uc_clock)
        s +="type: {}, \n".format(self.type)
        s +="trigg: {}".format(self.trigg)
        return s




class TriggerPacketData:
    @staticmethod
    def unpack(raw_packet: bytearray):
        magic_mark, mtype, mlen = TriggerPacketHeader.unpack(raw_packet[:4])

        if magic_mark != 0xCAFE:
            log.error(
                "Message magic marker malformed got %x instead of %x"
                % (magic_mark, 0xCAFE)
            )
            return None
        return NominalTriggerDataEncode.unpack(raw_packet[4:])

    def pack_header(mtype: int, mlength: int, magic_mark: int = 0xCAFE):
        raw_header = bytearray(TriggerPacketHeader.pack(magic_mark, mtype, mlength))
        return raw_header


class NominalTriggerDataEncode:
    NominalTriggerData = namedtuple(
        "NominalTriggerData", "TACK trigg uc_ev uc_pps uc_clock type"
    )
    tail_form = struct.Struct("<3I2H")

    @staticmethod
    def pack(
        tack: int,
        trigg_pat: bitarray,
        uc_ev: int,
        uc_pps: int,
        uc_clock: int,
        ttype: int,
    ):

        raw_packet = TriggerPacketData.pack_header(0x1, 22)
        raw_packet.extend(tack.to_bytes(8, "little"))
        raw_packet.extend(trigg_pat.tobytes())
        raw_packet.extend(
            NominalTriggerDataEncode.tail_form.pack(uc_ev, uc_pps, uc_clock, ttype, 0)
        )
        return raw_packet

    @staticmethod
    def unpack(raw_packet: bytearray):
        tack = int.from_bytes(raw_packet[:8], "little")
        tbits = bitarray(0, endian="little")
        tbits.frombytes(bytes(raw_packet[8:72]))

        tail = NominalTriggerDataEncode.tail_form.unpack(raw_packet[72:])
        return NominalTriggerDataEncode.NominalTriggerData(
            *[tack, tbits] + list(tail[:-1])
        )
