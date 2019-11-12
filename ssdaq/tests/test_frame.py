from ssdaq import data
import numpy as np

def test_ssreadout_serialization_and_deserialization():
    insreadout1 = data.SSReadout()
    insreadout2 = data.SSReadout()
    insreadout2.data[1] = 1923
    insreadout2.iro = 1
    frame1 = data.Frame()
    frame1.add("readout2", insreadout2)
    frame1.add("readout1", insreadout1)
    datastream = frame1.serialize()
    frame2 = data.Frame()
    frame2.deserialize_m(datastream)
    assert (
        list(frame1.keys()) == list(frame2.keys())
    ), "correct keys in deserialized frame"
    assert (
        frame1["readout2"].iro == frame2["readout2"].iro
    ), "correct readout number for in both frames"
    assert (
        frame1["readout1"].iro == frame2["readout1"].iro
    ), "correct readout number for in both frames"


def test_nominaltriggerpacket_serialization_and_deserialization():
    trigger_packet = data.NominalTriggerPacketV1(TACK=100)
    frame1 = data.Frame()
    frame1['trigg_pack'] = trigger_packet
    datastream = frame1.serialize()
    frame2 = data.Frame()
    frame2.deserialize_m(datastream)
    assert (
        list(frame1.keys()) == list(frame2.keys())
    ), "correct keys in deserialized frame"
    assert (
        frame1["trigg_pack"].tack_time == frame2["trigg_pack"].tack_time
    ), "Correct trigg TACK"

def test_triggerpacketV2_serialization_and_deserialization():
    trigger_packet = data.TriggerPacketV2(
                        tack_time=100,
                        )
    frame1 = data.Frame()
    frame1['trigg_pack'] = trigger_packet
    datastream = frame1.serialize()
    frame2 = data.Frame()
    frame2.deserialize_m(datastream)
    assert (
        list(frame1.keys()) == list(frame2.keys())
    ), "correct keys in deserialized frame"
    assert (
        frame1["trigg_pack"].tack_time == frame2["trigg_pack"].tack_time
    ), "Correct trigg TACK"

def test_triggerpacketV3_serialization_and_deserialization():
    trigger_packet = data.TriggerPacketV3(
                        tack_time=100,
                        )
    frame1 = data.Frame()
    frame1['trigg_pack'] = trigger_packet
    datastream = frame1.serialize()
    frame2 = data.Frame()
    frame2.deserialize_m(datastream)
    assert (
        list(frame1.keys()) == list(frame2.keys())
    ), "correct keys in deserialized frame"
    assert (
        frame1["trigg_pack"].tack_time == frame2["trigg_pack"].tack_time
    ),"Correct trigg TACK"

def test_log_message_serialization_and_deserialization():
    log_msg1 = data.LogData()
    log_msg1.message ='Hello World'
    log_msg1.systemType = 1
    log_msg1.severity = 10
    log_msg1.sender = 'Test'
    log_msg1.time = 1
    log_msg1.pid =0
    log_msg1.sourceFile = 'test'
    log_msg1.line = 0
    frame1 = data.Frame()
    frame1['msg'] = log_msg1
    datastream = frame1.serialize()
    frame2 = data.Frame()
    frame2.deserialize_m(datastream)
    assert (
        list(frame1.keys()) == list(frame2.keys())
    ), "correct keys in deserialized frame"
    assert (
        frame1["msg"].message == frame2["msg"].message
    ), "Correct log message"

def test_nested_frame_serialization_and_deserialization():
    trigger_packet = data.TriggerPacketV3(
                        tack_time=100,
                        )
    frame1 = data.Frame()
    frame1['trigg_pack'] = trigger_packet
    frame2 = data.Frame()
    frame2['frame1'] =frame1
    datastream = frame2.serialize()
    frame3 = data.Frame.deserialize(datastream)

    assert (
        list(frame2.keys()) == list(frame3.keys())
    ), "correct keys in deserialized frame"

    assert (
        frame1["trigg_pack"].tack_time == frame3['frame1']["trigg_pack"].tack_time
    ),"Correct trigg TACK"