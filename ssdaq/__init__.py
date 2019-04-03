import logging as _logging
from . import version

__version__ = version.get_version(pep440=False)


# This is the root logger for the core modules
sslogger = _logging.getLogger(__name__)
# Default formatter
_formatter = _logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
_handler = _logging.StreamHandler()
_handler.setFormatter(_formatter)
sslogger.addHandler(_handler)
sslogger.setLevel(_logging.INFO)


from .core.slowsignal.data import SSReadout
from .core.io.slowsignal_io import SSDataReader, SSDataWriter
from .core.slowsignal.readout_assembler import SSReadoutAssembler
from .core.publishers import ZMQTCPPublisher
from .subscribers.basicsubscriber import BasicSubscriber
from .subscribers.slowsignal import SSReadoutSubscriber, SSFileWriter
