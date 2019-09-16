import pytest
from ssdaq.receivers.readout_assembler import SlowSignalDataProtocol
import numpy as np
from unittest.mock import Mock
import datetime
import struct


@pytest.fixture
def mock_data_protocol():
    class Loop:
        def create_task(self, task):
            pass

    from queue import Queue
    import datetime

    mock_dp = Mock(SlowSignalDataProtocol)
    mock_dp._buffer = Queue()
    mock_dp.loop = Loop()
    mock_dp.log = lambda x: x  # log.getChild('SlowSignalDataProtocol')
    mock_dp.relaxed_ip_range = False
    mock_dp.dt = datetime.timedelta(seconds=0.1)
    mock_dp.datagram_received = SlowSignalDataProtocol.datagram_received.__get__(
        mock_dp
    )
    mock_dp.packet_debug_stream = False
    mock_dp.packet_format = struct.Struct(">Q32HQ32H")
    mock_dp.mon = Mock()
    mock_dp.mon.register_data_packet = Mock()
    return mock_dp


@pytest.fixture
def make_datapacket():
    def _make_datapacket(n=10, stime=100):
        time = stime
        data_packet = bytearray()
        for i in range(10):
            data_packet.extend(
                bytearray(
                    struct.pack(
                        ">Q32HQ32H",
                        time + int(i * 1e8),
                        *list(np.array(np.random.uniform(0, 400, 32), dtype=np.uint32)),
                        time + int(i * 1e8),
                        *list(np.array(np.random.uniform(0, 400, 32), dtype=np.uint32))
                    )
                )
            )
        return data_packet

    return _make_datapacket


def test_correct_cpu_timestamps(mock_data_protocol, make_datapacket):

    n = 10
    data_packet = make_datapacket(n=10)
    mock_data_protocol.datagram_received(data_packet, ("192.168.1.120", 2009))
    ros = []
    while not mock_data_protocol._buffer.empty():
        ros.append(mock_data_protocol._buffer.get())
    assert len(ros) == 1, "Correct number of readouts"
    assert ros[0][0] ==20, "Correct module number"
