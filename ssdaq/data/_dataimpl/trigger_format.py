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
        version and type of a trigger packet.
    """

    _message_types = {}

    def __init__(self):
        self._raw_packet = None

    @classmethod
    def register(cls, scls):
        cls._message_types[scls._mtype] = scls
        return scls

    @staticmethod
    def pack_header(version: int, magic_mark: int = 0xCAFE) -> bytearray:
        """Packs a trigger packet header into a byte array

        Args:
            version (int): Payload version
            magic_mark (int, optional): magic marker (for trigger packets
                it is set to 0xCAFE)

        Returns:
            bytearray: packet trigger packet header

        Payload version 0 and 1 are in fact the same version and the version
        number encodes whether the trigger i nominal (0) or busy (1). Newer payload
        versions have this information encoded in a seperate field.

        """
        raw_header = bytearray(TriggerPacketHeader.pack(magic_mark, version))
        return raw_header

    @classmethod
    def unpack(cls, raw_packet: bytearray):
        """Unpacks a bytestream into the appropriate trigger packet type
            and version.

        Args:
            raw_packet (bytearray): UDP payload

        Returns:
            TriggerPacket:  Instance of a descendant to TriggerPacket
        """
        magic_mark, mtype = TriggerPacketHeader.unpack(raw_packet[:3])

        if magic_mark != 0xCAFE:
            log.error(
                "Message magic marker malformed got %x instead of %x"
                % (magic_mark, 0xCAFE)
            )
            return None
        instance = TriggerPacket._message_types[mtype].unpack(raw_packet[3:])
        instance._raw_packet = raw_packet

        return instance

    def serialize(self) -> bytearray:
        """A convenience method to conform with the serialization api for instances
            of the class.

        Returns:
            bytearray: bytearray of the serialized (packed) trigger packet
        """
        return self.pack()

    @classmethod
    def deserialize(cls, raw_packet: bytearray):
        """ A convenience method to support "unpacking" for instances
            of the class.

        Args:
            raw_packet (bytearray): Description
        """
        return TriggerPacket.unpack(raw_packet)


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
    _head_form = struct.Struct("<BQB")#512H")
    _head_form2 = struct.Struct("<BQB")
    _tail_form = struct.Struct("<3IH")
    # used for reversing the bits of the phase byte
    _reverse_bits = dict([(2 ** i, 2 ** (7 - i)) for i in range(7, -1, -1)])

    def __init__(
        self,
        TACK: int = 0,
        trigg_phase: int = 1,
        trigg_phases: np.ndarray = np.zeros((16,512), dtype=np.uint8),
        trigg_union: bitarray = np.zeros(512, dtype=np.uint8),
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
        self._trigg_pattrns = trigg_phases
        self._trigg = None
        self._trigg_union = trigg_union

    def _compute_trigg(self):
        self._trigg = self._trigg_pattrns[self.phase_index, :]

    @property
    def busy(self):
        return self._busy

    @property
    def tack_time(self):
        return self._TACK

    @property
    def phase(self):
        return self._trigg_phase

    @property
    def ro_count(self):
        return self._uc_ev

    @property
    def pps_count(self):
        return self._uc_pps

    @property
    def clock_count(self):
        return self._uc_clock

    @property
    def source(self):
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
    def phase_index(self):
        """ Trigger phase index
            (an integer number between 0-8)
            corresponding to the position of
            phase bit

        Returns:
            int : phase index
        """
        return int(np.log2(self.phase + 1))

    @property
    def trigg_union(self):
        return self._trigg_union

    @classmethod
    def unpack(cls, raw_packet: bytearray):
        readout_length = 16
        # Extracting tack and trigger phase
        data_part1 = cls._head_form2.unpack(
            raw_packet[: cls._head_form2.size]
        )
        _, tack, phase = data_part1[0], data_part1[1], data_part1[2]
        phase = cls._reverse_bits[phase]

        # Extracting the triggered phases
        trigg_pattrns = np.unpackbits(np.frombuffer(
            raw_packet[
                cls._head_form.size : -int(512 / 8)
                - cls._tail_form.size
            ],
            dtype=np.uint8,
        ))
        trigg_pattrns = trigg_pattrns.reshape(512,readout_length).T
        # Extracting the trigger union
        union = np.unpackbits(
            np.frombuffer(
                raw_packet[cls._head_form.size +readout_length*int(512 / 8): -cls._tail_form.size],
                dtype=np.uint8,
            )
        )

        # extracting counters

        tail = cls._tail_form.unpack(
            raw_packet[-cls._tail_form.size :]
        )
        return cls(*[tack, phase, trigg_pattrns, union] + list(tail))

    def pack(self):

        raw_packet = super().pack_header(self._mtype)
        # #The phase is stored backwards
        phase = self._reverse_bits[self.phase]
        raw_packet.extend(self._head_form2.pack     (22, self.tack_time, phase))
        raw_packet.extend(np.packbits(self._trigg_pattrns.T).tobytes())
        raw_packet.extend(np.packbits(self._trigg_union).tobytes())
        raw_packet.extend(
            self._tail_form.pack(
                self.ro_count, self.pps_count, self.clock_count, self.source
            )
        )
        return raw_packet

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
        trigg_phases: np.ndarray = np.zeros((16,512), dtype=np.uint16),
        trigg_union: bitarray = np.zeros(512, dtype=np.uint16),
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
class TriggerPacketV2(TriggerPacket):

    """ Trigger packet version 2. Contains trigger patterns
        for the whole readout window and encodes the busy flag
        in the message type.

    """

    _mtype = 0x2
    _reverse_bits = dict([(2 ** i, 2 ** (7 - i)) for i in range(7, -1, -1)])
    _head_form = struct.Struct("<2BHBQB3I")

    def __init__(
        self,
        message_type: int = 0,
        error_flags: int = 0,
        source: int = 0,
        tack_time: int = 0,
        phase: int = 1,
        ro_count: int = 0,
        pps_count: int = 0,
        clock_count: int = 0,
        trigg_pattrns=np.ones((128, 512), dtype=np.uint8),
    ):
        """
        Args:
            message_type (int, optional): Type of trigger packet (first bit indicates busy)
            error_flags (int, optional): Debug error flags (non-zero indicates error)
            source (int, optional): Trigger source
            tack_time (int, optional): TACK time stamp
            phase (int, optional): Trigger phase bit
            ro_count (int, optional): readout count
            pps_count (int, optional): pulse per second count
            clock_count (int, optional): clock count
            trigg_pattrns (np.array type uint8, optional): Trigger patterns of `n` readouts. numpy array of shape (n,512)

        """
        self._message_type = message_type
        self._error_flags = error_flags
        self._source = source
        self._tack_time = tack_time
        self._phase = phase
        self._ro_count = ro_count
        self._pps_count = pps_count
        self._clock_count = clock_count
        self._trigg_pattrns = trigg_pattrns
        self._readout_length = self._trigg_pattrns.shape[0]
        trigg_SPs = np.any(self._trigg_pattrns, axis=0)
        self._trigg_union = trigg_SPs  # bitarray(trigg_SPs.data, endian="little")
        self._trigg = None

    def _compute_trigg(self):
        self._trigg = self._trigg_pattrns[self.phase_index, :]

    @property
    def message_type(self):
        return self._message_type

    @property
    def error_flags(self):
        return self._error_flags

    @property
    def source(self):
        return self._source

    @property
    def readout_length(self):
        return self._readout_length

    @property
    def tack_time(self):
        return self._tack_time

    @property
    def phase(self):
        """ Trigger phase bit

        Returns:
            int: phase
        """
        return self._phase

    @property
    def phase_index(self):
        """ Trigger phase index
            (an integer number between 0-8)
            corresponding to the position of
            phase bit

        Returns:
            int : phase index
        """
        return int(np.log2(self._phase + 1))

    @property
    def ro_count(self):
        return self._ro_count

    @property
    def pps_count(self):
        return self._pps_count

    @property
    def clock_count(self):
        return self._clock_count

    @property
    def trigg(self):
        if self._trigg is None:
            self._compute_trigg()
        return self._trigg

    @property
    def trigg_union(self):
        return self._trigg_union

    @property
    def trigg_pattrns(self):
        return self._trigg_pattrns

    @property
    def busy(self):
        return self.message_type&1 == 1

    def __str__(self):
        s = "<{}>   ".format(self.__class__.__name__)
        s += "TACK: {}, ".format(self.tack_time)
        s += "trigger_phase: {}, ".format(self.phase_index)
        s += "ro_count: {}, ".format(self.ro_count)
        s += "pps_count: {}, ".format(self.pps_count)
        s += "clock_count: {}, ".format(self.clock_count)
        s += "source: {}, \n".format(self.source)
        s += "trigg: {}".format(self.trigg)

        return s

    @classmethod
    def unpack(cls, raw_packet: bytearray):
        """ Unpacks a V2 trigger packet

        Args:
            raw_packet (bytearray): the raw payload not including the 3 first bytes
        """
        head_form = cls._head_form
        header = list(head_form.unpack(raw_packet[: head_form.size]))

        # The phase bits are backwards in the trigger packet
        header[5] = cls._reverse_bits[header[5]]
        ro_len = header[3] * 8
        # The readout length is not needed for the class instantiation
        del header[3]

        # Extracting the triggered phases (trigger pattern readout) in chunks of 8 bits
        trigg_pattrns = np.frombuffer(
            raw_packet[head_form.size + int(512 / 8) :], dtype=np.uint8
        )
        trigg_pattrns = (
            np.unpackbits(trigg_pattrns).reshape((512, ro_len))
        ).T  # we want the rows to be the time axis

        return cls(*header + [trigg_pattrns])

    def pack(self):
        raw_packet = super().pack_header(self._mtype)
        raw_packet.extend(
            self._head_form.pack(
                self._message_type,
                self._error_flags,
                self._source,
                int(self._readout_length // 8),
                self._tack_time,
                self._reverse_bits[self._phase],
                self._ro_count,
                self._pps_count,
                self._clock_count,
            )
        )
        raw_packet.extend(np.packbits(self._trigg_union).tobytes())
        raw_packet.extend(np.packbits((self._trigg_pattrns.T)).tobytes())
        return raw_packet


@TriggerPacket.register
class TriggerPacketV3(TriggerPacketV2):

    """ Similar to V2 in containing trigger patterns
        for the complete readout. The readout data is,
        however, zero-point suppressed to reduce droped
        packets at high trigger rates.
    """

    _mtype = 0x3

    @classmethod
    def unpack(cls, raw_packet: bytearray):
        """ Unpacks a V3 trigger packet

        Args:
            raw_packet (bytearray): the raw payload not including the 3 first bytes
        """
        head_form = cls._head_form
        header = list(head_form.unpack(raw_packet[: head_form.size]))

        # The phase bits are backwards in the trigger packet
        header[5] = cls._reverse_bits[header[5]]

        union = np.unpackbits(
            np.frombuffer(
                raw_packet[head_form.size : head_form.size + int(512 / 8)],
                dtype=np.uint8,
            )
        )
        ro_len = header[3] * 8
        # The readout length is not needed for the class instantiation
        del header[3]

        # Extracting the triggered phases (trigger pattern readout)
        triggered_pattrns = np.frombuffer(
            raw_packet[head_form.size + int(512 / 8) :], dtype=np.uint8
        )
        triggered_pattrns = (
            np.unpackbits(triggered_pattrns).reshape((512, ro_len))
        ).T  # we want the rows to be the time axis
        trigg_pattrns = np.zeros((ro_len, 512),dtype=np.uint8)
        trigg_pattrns[:, np.where(union)[0]] = triggered_pattrns

        return cls(*header + [trigg_pattrns])

    def pack(self):
        raw_packet = super().pack_header(self._mtype)
        raw_packet.extend(
            self._head_form.pack(
                self._message_type,
                self._error_flags,
                self._source,
                int(self._readout_length // 8),
                self._tack_time,
                self._reverse_bits[self._phase],
                self._ro_count,
                self._pps_count,
                self._clock_count,
            )
        )
        raw_packet.extend(np.packbits(self._trigg_union).tobytes())
        trigg_SPs = np.where(np.any(self._trigg_pattrns, axis=0))[0]
        triggered_pattrns = np.packbits(self._trigg_pattrns[:, trigg_SPs].T)
        raw_packet.extend(triggered_pattrns.tobytes())
        return raw_packet
