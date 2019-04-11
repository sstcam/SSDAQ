import logging
import logging.handlers
from ssdaq.core.logging import log_pb2
from datetime import datetime
import os


class ChecSocketLogHandler(logging.handlers.SocketHandler):
    def makePickle(self, record):
        logdata = log_pb2.LogData()
        logdata.systemType = 0
        logdata.severity = record.levelno
        logdata.sender = record.name
        logdata.message = record.msg
        logdata.time = int(datetime.utcnow().timestamp() * 1e9)
        logdata.pid = os.getpid()
        logdata.sourceFile = record.pathname
        logdata.line = record.lineno
        return logdata.SerializeToString()


def parseprotb2log(data: bytes) -> log_pb2.LogData:
    log = log_pb2.LogData()
    log.ParseFromString(data)
    return log


def protb2logrecord(proto: log_pb2.LogData) -> logging.LogRecord:
    record = logging.LogRecord(
        name=proto.sender,
        level=proto.severity,
        pathname=proto.sourceFile,
        lineno=proto.line,
        msg=proto.message,
        args=None,
        exc_info=None,
        func=proto.sender,
        sinfo="",
    )
    record.pid = proto.pid
    record.created = proto.time * 1e-9
    return record


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# The background is set with 40 plus the number of the color, and the foreground with 30

# These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"


def formatter_message(message, use_color=True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


COLORS = {
    "WARNING": YELLOW,
    "INFO": WHITE,
    "DEBUG": BLUE,
    "CRITICAL": YELLOW,
    "ERROR": RED,
}


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = (
                COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            )
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


# Custom logger class with multiple destinations
class ColoredLogger(logging.Logger):
    FORMAT = "[$BOLD%(name)-20s$RESET][%(levelname)-18s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
    COLOR_FORMAT = formatter_message(FORMAT, True)

    def __init__(self, name):
        logging.Logger.__init__(self, name, logging.DEBUG)

        color_formatter = ColoredFormatter(self.COLOR_FORMAT)

        console = logging.StreamHandler()
        console.setFormatter(color_formatter)

        self.addHandler(console)
        return
