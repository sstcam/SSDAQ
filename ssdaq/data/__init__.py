from ._dataimpl import LogData
from ._dataimpl import TimeUTC
from ._dataimpl import MonitorData
from ._dataimpl import MonitorFrame

from ._dataimpl import TimeStamp
from ._dataimpl import TriggerMessage
from ._dataimpl import TriggerBunch
from ._dataimpl import TelData

from ._dataimpl.frame import Frame, FrameObject
from ._dataimpl import SSReadout
from ._dataimpl.trigger_format import (
    TriggerPacket,
    NominalTriggerPacketV1,
    BusyTriggerPacketV1,
)


class SSReadoutFrame(FrameObject, SSReadout):
    def __init__(self):
        SSReadout.__init__(self)
        FrameObject.__init__(self, self.pack, self.unpack)


# class SSReadoutFrame(FrameObject,SSReadout):
#     def __init__(self):
#         SSReadout.__init__(self)
#         FrameObject.__init__(self.pack,self.unpac)
