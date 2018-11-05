import logging as _logging
from .core.SSEventBuilder import SSEventBuilder
from .core.SSEventBuilder import SSEvent
from .core.SSEventDataPublisher import SSEventDataPublisher
from .core.SSDataListener import SSDataListener
from .core.SSEventListener import SSEventListener

sslogger = _logging.getLogger(__name__)#.addHandler(_logging.NullHandler())
formatter = _logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler = _logging.StreamHandler()

handler.setFormatter(formatter)
sslogger.addHandler(handler)
sslogger.setLevel(_logging.INFO)
