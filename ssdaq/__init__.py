import logging as _logging
from .core.ss_data_classes import SSReadout,SSDataReader, SSDataWriter
from .core.ss_event_builder import SSReadoutAssembler, ZMQReadoutPublisher
from .core.ss_event_listener import SSReadoutListener


#This is the root logger for the core modules
sslogger = _logging.getLogger(__name__)
#Default formatter
_formatter = _logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
_handler = _logging.StreamHandler()
_handler.setFormatter(_formatter)
sslogger.addHandler(_handler)
sslogger.setLevel(_logging.INFO)
