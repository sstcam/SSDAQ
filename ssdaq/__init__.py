import logging as _logging

from .core.SSEventBuilder import SSEventBuilder
from .core.SSEventBuilder import SSEvent
from .core.SSEventDataPublisher import SSEventDataPublisher
from .core.SSDataListener import SSDataListener
from .core.SSEventListener import SSEventListener


#This is the root logger for the core modules
sslogger = _logging.getLogger(__name__)
#Default formatter
_formatter = _logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
_handler = _logging.StreamHandler()
_handler.setFormatter(_formatter)
sslogger.addHandler(_handler)
sslogger.setLevel(_logging.INFO)
