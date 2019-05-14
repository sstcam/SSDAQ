# from ._dataimpl.log_pb2 import LogData
# from ._dataimpl.monitor_pb2 import TimeUTC
# from ._dataimpl.monitor_pb2 import MonitorData
# from ._dataimpl.monitor_pb2 import MonitorFrame

# from ._dataimpl.CDTS_pb2 import TimeStamp
# from ._dataimpl.CDTS_pb2 import TriggerMessage
# from ._dataimpl.CDTS_pb2 import TriggerBunch
# from ._dataimpl.teldata_pb2 import TelData

from ._dataimpl import LogData
from ._dataimpl import TimeUTC
from ._dataimpl import MonitorData
from ._dataimpl import MonitorFrame

from ._dataimpl import TimeStamp
from ._dataimpl import TriggerMessage
from ._dataimpl import TriggerBunch
from ._dataimpl import TelData

from ._dataimpl.frame import Frame, FrameObject
from ._dataimpl.slowsignal_format import SSReadout
from ._dataimpl.trigger_format import TriggerPacketData
from ._dataimpl.trigger_format import NominalTriggerDataEncode


class SSReadoutFrame(FrameObject, SSReadout):
    def __init__(self):
        SSReadout.__init__(self)
        FrameObject.__init__(self, self.pack, self.unpack)


# class SSReadoutFrame(FrameObject,SSReadout):
#     def __init__(self):
#         SSReadout.__init__(self)
#         FrameObject.__init__(self.pack,self.unpac)
