from ssdaq import data


def test_ssreadout_frame_serialization_and_deserialization():
    insreadout1 = data.SSReadoutFrame()
    insreadout2 = data.SSReadoutFrame()
    insreadout2.data[1] = 1923
    insreadout2.iro = 1
    frame1 = data.Frame()
    frame1.add("readout2", insreadout2)
    frame1.add("readout1", insreadout1)
    datastream = frame1.serialize()
    frame2 = data.Frame()
    frame2.deserialize(datastream)
    assert (
        frame1._objects.keys() == frame2._objects.keys()
    ), "correct keys in deserialized frame"
    assert (
        frame1._objects["readout2"].iro == frame2._objects["readout2"].iro
    ), "correct readout number for in both frames"
    assert (
        frame1._objects["readout1"].iro == frame2._objects["readout1"].iro
    ), "correct readout number for in both frames"
