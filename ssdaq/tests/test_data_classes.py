import pytest
from ssdaq.data import (
    SSReadout,
    BusyTriggerPacketV1,
    NominalTriggerPacketV1,
    TriggerPacketV2,
    TriggerPacketV3,
    TriggerPacket,
)
import numpy as np


def test_pack_unpack():
    readout1 = SSReadout(
        timestamp=12345, readout_number=1234, cpu_t_s=1234, cpu_t_ns=1234
    )
    readout1.data[2, :] = np.arange(64)
    readout1.data[3, :] = np.arange(64)
    packed_readout = readout1.pack()
    readout2 = SSReadout()
    readout2.unpack(packed_readout)

    assert readout1.iro == readout2.iro, "correct readout number"
    assert readout1.time == readout2.time, "correct timestamp TACK"
    assert readout1.cpu_t == readout2.cpu_t, "correct native timestamp cpu"
    assert readout1.cpu_t_s == readout2.cpu_t_s, "correct timestamp cpu seconds"
    assert readout1.cpu_t_ns == readout2.cpu_t_ns, "correct timestamp cpu nano seconds"
    assert (readout1.data[2] == readout2.data[2]).all(), "correct readout"
    assert (readout1.data[3] == readout2.data[3]).all(), "correct readout"
    assert not (readout1.data[4] == readout2.data[4]).all(), "correct readout"
    assert np.isnan(readout1.data[4, 0]), "nans for empty readouts"


def test_trigger_packet_pack_unpack():
    trigg = BusyTriggerPacketV1(
        trigg_phases=2 ** np.random.uniform(0, 15, 512),
        trigg_phase=2 ** int(np.random.uniform(0, 7)),
    )

    triggun = TriggerPacket.unpack(trigg.pack())
    assert triggun.phase == trigg.phase, "correct phase"
    assert np.all(triggun.trigg == trigg.trigg), "correct trigger pattern V1"
    assert triggun.busy == trigg.busy, "correct busy flag"
    assert np.all(triggun.trigg_union == trigg.trigg_union), "correct union of triggers"

    triggV2 = TriggerPacketV2(
        # trigg_union = 2 ** np.random.uniform(0, 15, 512)
        trigg_pattrns=np.array(np.random.uniform(0, 2, (128, 512)), dtype=np.uint8),
        phase=2 ** int(np.random.uniform(0, 7)),
    )

    triggunV2 = TriggerPacket.unpack(triggV2.pack())
    assert triggunV2.phase == triggV2.phase, "correct phase"
    assert np.all(
        triggunV2.trigg_pattrns == triggV2.trigg_pattrns
    ), "correct trigger pattern V2"
    triggV3 = TriggerPacketV3(
        # trigg_union = 2 ** np.random.uniform(0, 15, 512)
        trigg_pattrns=np.array(np.random.uniform(0, 2, (128, 512)), dtype=np.uint8),
        phase=2 ** int(np.random.uniform(0, 7)),
        message_type=5
    )

    triggunV3 = TriggerPacket.unpack(triggV3.pack())
    assert triggunV3.phase == triggV3.phase, "correct phase V3"
    assert triggunV3.busy, "is busy"
    assert np.all(
        triggunV3.trigg_pattrns == triggV3.trigg_pattrns
    ), "correct trigger pattern V3"
