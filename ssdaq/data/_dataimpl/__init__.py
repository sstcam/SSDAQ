from .log_pb2 import LogData as _LogData
from .monitor_pb2 import TimeUTC as _TimeUTC
from .monitor_pb2 import MonitorData as _MonitorData
from .monitor_pb2 import MonitorFrame as _MonitorFrame
from .CDTS_pb2 import TimeStamp as _TimeStamp
from .CDTS_pb2 import TriggerMessage as _TriggerMessage
from .CDTS_pb2 import TriggerBunch as _TriggerBunch
from .teldata_pb2 import TelData as _TelData

# from .trigger_format import TriggerPacketData
# from .trigger_format import NominalTriggerDataEncode
from .trigger_format import TriggerPacket
from .trigger_format import (
    NominalTriggerPacketV1,
    BusyTriggerPacketV1,
)
from .slowsignal_format import SSReadout

# from .frame import Frame, FrameObject


class ProtoWrapper:
    def __init__(self, cls):
        self._cls = cls
        for k, v in cls.DESCRIPTOR.fields_by_name.items():
            setattr(
                self.__class__,
                k,
                property(
                    lambda self, k=k: self._cls.__getattribute__(k),
                    lambda self, v, k=k: self._cls.__setattr__(k, v),
                    doc=self._cls.__getattribute__(k).__doc__,
                ),
            )
        self.SerializeToString = self._cls.SerializeToString
        self.ParseFromString = self._cls.ParseFromString

    def serialize(self):
        return self._cls.SerializeToString()

    def deserialize(self, data):
        self._cls.ParseFromString(data)

    def __repr__(self):
        return self._cls.__repr__()


class LogData(ProtoWrapper):
    def __init__(self):
        super().__init__(_LogData())


class TimeUTC(ProtoWrapper):
    def __init__(self):
        super().__init__(_TimeUTC())


class MonitorData(ProtoWrapper):
    def __init__(self):
        super().__init__(_MonitorData())


class MonitorFrame(ProtoWrapper):
    def __init__(self):
        super().__init__(_MonitorFrame())


class TimeStamp(ProtoWrapper):
    def __init__(self):
        super().__init__(_TimeStamp())


class TriggerMessage(ProtoWrapper):
    def __init__(self):
        super().__init__(_TriggerMessage())


class TriggerBunch(ProtoWrapper):
    def __init__(self):
        super().__init__(_TriggerBunch())


class TelData(ProtoWrapper):
    def __init__(self):
        super().__init__(_TelData())
