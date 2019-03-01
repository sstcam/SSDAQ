import pytest
from ssdaq import SSReadout
import numpy as np

def test_pack_unpack():
    readout1 = SSReadout(timestamp = 12345,readout_number=1234,cpu_t=1234)
    readout1.data[2,:] = np.arange(64)
    readout1.data[3,:] = np.arange(64)
    packed_readout = readout1.pack()
    readout2 = SSReadout()
    readout2.unpack(packed_readout)

    assert readout1.readout_number == readout2.readout_number, 'correct readout number'
    assert readout1.readout_timestamp == readout2.readout_timestamp, 'correct timestamp'
    assert (readout1.data[2]==readout2.data[2]).all(), 'correct readout'
    assert (readout1.data[3]==readout2.data[3]).all(), 'correct readout'
    assert not (readout1.data[4]==readout2.data[4]).all(), 'correct readout'
    assert np.isnan(readout1.data[4,0]), 'nans for empty readouts'