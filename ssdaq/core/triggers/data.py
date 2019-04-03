import struct
from collections import namedtuple
from ssdaq import sslogger
from bitarray import bitarray

log = sslogger.getChild("trigger_data")

TriggerPacketHeader = struct.Struct("<H2B")


class TriggerPacketData:
    @staticmethod
    def unpack(raw_packet: bytearray):
        magic_mark, mtype, mlen = TriggerPacketHeader.unpack(raw_packet[:4])

        if magic_mark != 0xCAFE:
            log.error("Message magic marker malformed")
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
