import pytest
from ssdaq.data import (
    SSReadout,
    BusyTriggerPacketV2,
    NominalTriggerPacketV2,
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
    trigg = BusyTriggerPacketV2(
        trigg_phases=2 ** np.random.uniform(0, 15, 512),
        trigg_phase=2 ** int(np.random.uniform(0, 7)),
    )

    triggun = TriggerPacket.unpack(trigg.pack())
    assert np.all(triggun.trigg == trigg.trigg), "correct trigger pattern"
    assert triggun.busy == trigg.busy, "correct busy flag"
    assert np.all(triggun.trigg_union == trigg.trigg_union), "correct union of triggers"
