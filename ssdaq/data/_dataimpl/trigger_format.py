import struct
from ssdaq import sslogger
from bitarray import bitarray
import numpy as np
from ssdaq.core.utils import get_attritbues

log = sslogger.getChild("trigger_data")
TriggerPacketHeader = struct.Struct("<HB")


def get_SP2bptrigg_mapping():
    """ Returns the mapping of SPs to back plane triggers

    Returns:
        np.array: array containing the mapping
    """
    fMask2SPA = np.array([6, 7, 14, 12, 4, 5, 15, 13, 3, 2, 8, 11, 1, 0, 10, 9])
    fMask2SPB = np.array([9, 10, 0, 1, 11, 8, 2, 3, 13, 15, 5, 4, 12, 14, 7, 6])
    masks = [fMask2SPA, fMask2SPB]
    sel = [0, 1, 0, 1] + [1, 0] * 12 + [0, 1, 0, 1]
    m = np.zeros(512, dtype=np.uint64)
    for i, s in enumerate(sel):
        m[i * 16 : i * 16 + 16] = masks[s] + i * 16
    return m


def get_bptrigg2SP_mapping():
    """ Returns the mapping of backplane triggers to SPs

    Returns:
        TYPE: array containing the mapping
    """
    fSP2MaskA = np.array([13, 12, 9, 8, 4, 5, 0, 1, 10, 15, 14, 11, 3, 7, 2, 6])
    fSP2MaskB = np.array([2, 3, 6, 7, 11, 10, 15, 14, 5, 0, 1, 4, 12, 8, 13, 9])
    masks = [fSP2MaskA, fSP2MaskB]
    sel = [0, 1, 0, 1] + [1, 0] * 12 + [0, 1, 0, 1]
    m = np.zeros(512, dtype=np.uint64)
    for i, s in enumerate(sel):
        m[i * 16 : i * 16 + 16] = masks[s] + i * 16
    return m


class TriggerPacket:

    """ Base class for trigger packets. All trigger packet classes should
        derive from this class and register. This class knows how to pack
        and unpack the first bytes of the trigger payload. Using the information
        in the first bytes it will in the unpack method instantiate the correct
        version and type of trigger packet.
    """

    _message_types = {}

    def __init__(self):
        pass

    @classmethod
    def register(cls, scls):
        cls._message_types[scls._mtype] = scls
        return scls

    @staticmethod
    def pack_header(mtype: int, magic_mark: int = 0xCAFE)->bytearray:
        """Packs a trigger packet header into a byte array

        Args:
            mtype (int): Description
            mlength (int): Description
            magic_mark (int, optional): Description

        Returns:
            bytearray: packet trigger packet header
        """
        raw_header = bytearray(TriggerPacketHeader.pack(magic_mark, mtype))
        return raw_header

    @classmethod
    def unpack(cls, data:bytearray):
        """Unpacks a bytestream into the appropriate trigger packet type
            and version.

        Args:
            data (bytearray): Description

        Returns:
            TYPE:  Instance of a descendant to TriggerPacket
        """
        magic_mark, mtype = TriggerPacketHeader.unpack(data[:3])

        if magic_mark != 0xCAFE:
            log.error(
                "Message magic marker malformed got %x instead of %x"
                % (magic_mark, 0xCAFE)
            )
            return None
        instance =TriggerPacket._message_types[mtype].unpack(data[3:])
        instance._raw_packet = data
        return instance

    def deserialize(self, data:bytearray):
        """ A convenience method to support "unpacking" for instances
            of the class.

        Args:
            data (bytearray): Description
        """
        inst = TriggerPacket.unpack(data)
        self.__dict__.update(inst.__dict__)

    def _asdict(self):
        return get_attritbues(self)



@TriggerPacket.register
class NominalTriggerPacketV1(TriggerPacket):

    """ Nominal Trigger packet V1. Contains triggered phases
        from the first two blocks, which corresponds to a trigger
        pattern readout window of 9-16 ns depending on which
        phase was triggered.
    """

    _mtype = 0x0
    _head_form = struct.Struct("<BQB512H")
    _head_form2 = struct.Struct("<BQB")
    _tail_form = struct.Struct("<3IH")
    #used for reversing the bits of the phase byte
    _reverse_bits = dict([(2**i,2**(7-i)) for i in range(7,-1,-1)])
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
        """

        Args:
            TACK (int, optional): TACK time stamp
            trigg_phase (int, optional): The trigger phase i (i=[0,7]) in the form 2^i
            trigg_phases (np.ndarray, optional): Triggered phases for the first two trigger blocks (up to 16 phases)
            trigg_union (bitarray, optional): The union of all triggers during readout
            uc_ev (int, optional): UC event counter
            uc_pps (int, optional): UC pps (pulse per second) counter
            uc_clock (int, optional): UC clock counter
            type_ (int, optional): Trigger type
        """
        super().__init__()
        self._TACK = TACK
        self._trigg_phase = trigg_phase
        self._uc_ev = uc_ev
        self._uc_pps = uc_pps
        self._uc_clock = uc_clock
        self._type = type_
        self._busy = False
        self._mtype = NominalTriggerPacketV1._mtype
        self._trigger_phases = np.array(trigg_phases, dtype=np.uint16)
        self._trigg = None
        self._trigg_union = trigg_union

    def _compute_trigg(self):
        trigg_phase_array = np.ones(self._trigger_phases.shape, dtype=np.uint16) * (self.trigg_phase)

        self._trigg = (
            np.bitwise_and(trigg_phase_array, self._trigger_phases) > 0
        ).astype(np.uint16)

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
        #Extracting tack and trigger phase
        data_part1 = NominalTriggerPacketV1._head_form2.unpack(
            raw_packet[:NominalTriggerPacketV1._head_form2.size]
        )
        _, tack, phase = data_part1[0], data_part1[1], data_part1[2]
        phase = NominalTriggerPacketV1._reverse_bits[phase]

        #Extracting the triggered phases
        trigg_phases = np.frombuffer(raw_packet[NominalTriggerPacketV1._head_form2.size: -int(512 / 8) - NominalTriggerPacketV1._tail_form.size],dtype=np.uint16)

        #Extracting the trigger union
        tbits = bitarray(0, endian="little")
        tbits.frombytes(
            bytes(
                raw_packet[
                    NominalTriggerPacketV1._head_form.size: -NominalTriggerPacketV1._tail_form.size
                ]
            )
        )
        #extracting counters
        tail = NominalTriggerPacketV1._tail_form.unpack(
            raw_packet[-NominalTriggerPacketV1._tail_form.size :]
        )
        return cls(
            *[tack, phase,trigg_phases , tbits]
            + list(tail)
        )

    def pack(self):

        raw_packet = super().pack_header(self._mtype)
        # #The phase is stored backwards
        phase = NominalTriggerPacketV1._reverse_bits[self.trigg_phase]
        raw_packet.extend(NominalTriggerPacketV1._head_form2.pack(22,self.TACK,phase))
        raw_packet.extend(self._trigger_phases.tobytes())
        raw_packet.extend(self._trigg_union.tobytes())
        raw_packet.extend(
            NominalTriggerPacketV1._tail_form.pack(
                self.uc_ev, self.uc_pps, self.uc_clock, self.type
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
class BusyTriggerPacketV1(NominalTriggerPacketV1):

    """ Busy trigger packet V1. Has the same layot as the nominal
        trigger packet V1 but represents a busy trigger, i.e a trigger
        that did not cause a readout.
    """

    _mtype = 0x1

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
        """

        Args:
            TACK (int, optional): TACK time stamp
            trigg_phase (int, optional): The trigger phase i (i=[0,7]) in the form 2^i
            trigg_phases (np.ndarray, optional): Triggered phases for the first two trigger blocks (up to 16 phases)
            trigg_union (bitarray, optional): The union of all triggers during readout
            uc_ev (int, optional): UC event counter
            uc_pps (int, optional): UC pps (pulse per second) counter
            uc_clock (int, optional): UC clock counter
            type_ (int, optional): Trigger type
        """
        super().__init__(
            TACK, trigg_phase, trigg_phases, trigg_union, uc_ev, uc_pps, uc_clock, type_
        )
        self._busy = True
        self._mtype = BusyTriggerPacketV1._mtype



@TriggerPacket.register
class NominalTriggerPacketV2(TriggerPacket):
    _mtype = 0x2
    _reverse_bits = dict([(2**i,2**(7-i)) for i in range(7,-1,-1)])
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
        pass