import logging
import os
from datetime import datetime
from threading import Thread
from ssdaq import sslogger
from ssdaq.core import (
    BasicSubscriber,
    WriterSubscriber,
    AsyncSubscriber,
    AsyncWriterSubscriber,
)
from ssdaq import logging as handlers
from ssdaq.data import (
    io,
    TriggerPacket,
    TriggerMessage,
    SSReadout,
    MonitorData,
    TelData,
)
from ssdaq.core.utils import get_si_prefix


class SSReadoutSubscriber(BasicSubscriber):
    """A slow signal subscriber
    """

    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        """ Init of a SSReadoutSubscriber

        Args:
            ip (str): The ip/interface where the data is published
            port (int): The port on which the data is published
            logger (logging.Logger, optional): A logger instance
        """
        super().__init__(ip=ip, port=port, logger=logger, unpack=SSReadout.from_bytes)


class AsyncSSReadoutSubscriber(AsyncSubscriber):
    def __init__(
        self, ip: str, port: int, logger: logging.Logger = None, loop=None, name=None
    ):
        super().__init__(
            ip=ip,
            port=port,
            logger=logger,
            unpack=SSReadout.from_bytes,
            loop=loop,
            name=name,
        )


class BasicTriggerSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        """ Init of a BasicTriggerSubscriber

        Args:
            ip (str): The ip/interface where the data is published
            port (int): The port on which the data is published
            logger (logging.Logger, optional): A logger instance
        """

        super().__init__(ip=ip, port=port, logger=logger, unpack=TriggerPacket.unpack)


class AsyncTriggerSubscriber(AsyncSubscriber):
    def __init__(
        self, ip: str, port: int, logger: logging.Logger = None, loop=None, name=None
    ):
        super().__init__(
            ip=ip,
            port=port,
            logger=logger,
            unpack=TriggerPacket.unpack,
            loop=loop,
            name=name,
        )


logunpack = lambda x: handlers.protb2logrecord(handlers.parseprotb2log(x))


class BasicLogSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, logger=logger, unpack=logunpack)


class AsyncLogSubscriber(AsyncSubscriber):
    def __init__(
        self, ip: str, port: int, logger: logging.Logger = None, loop=None, name=None
    ):
        super().__init__(
            ip=ip, port=port, logger=logger, unpack=logunpack, loop=loop, name=name
        )


def timeunpack(x):
    tmsg = TriggerMessage()
    tmsg.ParseFromString(x)
    return tmsg


class BasicTimestampSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, logger=logger, unpack=timeunpack)


class AsyncTimestampSubscriber(AsyncSubscriber):
    def __init__(
        self, ip: str, port: int, logger: logging.Logger = None, loop=None, name=None
    ):
        super().__init__(
            ip=ip, port=port, logger=logger, unpack=timeunpack, loop=loop, name=name
        )


def monunpack(x):
    monmsg = MonitorData()
    monmsg.ParseFromString(x)
    return monmsg


class BasicMonSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, logger=logger, unpack=monunpack)


class AsyncMonSubscriber(AsyncSubscriber):
    def __init__(
        self, ip: str, port: int, logger: logging.Logger = None, loop=None, name=None
    ):
        super().__init__(
            ip=ip, port=port, logger=logger, unpack=monunpack, loop=loop, name=name
        )


logprotounpack = lambda x: handlers.parseprotb2log(x)


class LogProtoSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, logger=logger, unpack=logprotounpack)


class AsyncLogProtoSubscriber(AsyncSubscriber):
    def __init__(
        self, ip: str, port: int, logger: logging.Logger = None, loop=None, name=None
    ):
        super().__init__(
            ip=ip, port=port, logger=logger, unpack=logprotounpack, loop=loop, name=name
        )


# These are locals in init that we want to skip
# when creating the kwargs dict
skip = ["self", "__class__"]


class LogWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):
        super().__init__(
            subscriber=LogProtoSubscriber,
            writer=io.LogWriter,
            file_ext=".sof",
            name="LogWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )


class TimestampWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):

        super().__init__(
            subscriber=BasicTimestampSubscriber,
            writer=io.TimestampWriter,
            file_ext=".sof",
            name="TimestampWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )
        print(locals())


class ATimestampWriter(AsyncWriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
        loop=None,
        name="ATimestampWriter",
    ):
        super().__init__(
            subscriber=AsyncTimestampSubscriber,
            writer=io.TimestampWriter,
            file_ext=".prt",
            **{k: v for k, v in locals().items() if k not in skip}
        )


class TriggerWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):
        super().__init__(
            subscriber=BasicTriggerSubscriber,
            writer=io.TriggerWriter,
            file_ext=".sof",
            name="TriggerWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )


class SSFileWriter(WriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
    ):
        super().__init__(
            subscriber=SSReadoutSubscriber,
            writer=io.SSDataWriter,
            file_ext=".hdf5",
            name="SSFileWriter",
            **{k: v for k, v in locals().items() if k not in skip}
        )

    def data_cond(self, data):
        return data.iro == 1 and self.data_counter > 0


class ATriggerWriter(AsyncWriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
        loop=None,
        name="ATriggerWriter",
    ):
        super().__init__(
            subscriber=AsyncSubscriber,
            writer=io.RawTriggerWriter,
            file_ext=".sof",
            **{k: v for k, v in locals().items() if k not in skip}
        )


def teldataunpack(data):
    teldata = TelData()
    teldata.ParseFromString(data)
    return teldata


class ASlowSignalWriter(AsyncWriterSubscriber):
    def __init__(
        self,
        file_prefix: str,
        ip: str,
        port: int,
        folder: str = "",
        file_enumerator: str = None,
        filesize_lim: int = None,
        loop=None,
        name="ASlowSignalWriter",
    ):
        super().__init__(
            subscriber=AsyncSSReadoutSubscriber,
            writer=io.SSDataWriter,
            file_ext=".hdf5",
            **{k: v for k, v in locals().items() if k not in skip}
        )

        self._teldatasub = AsyncSubscriber(
            ip="127.0.0.101",
            port=9006,
            unpack=teldataunpack,
            logger=self.log,
            zmqcontext=self._subscriber.context,
            loop=self.loop,
            passoff_callback=self.write_tel_data,
            name="telsub",
        )
        self.log = sslogger.getChild(name)

    def write_tel_data(self, data):
        self._writer.write_tel_data(
            ra=data.ra,
            dec=data.dec,
            time=data.time.sec + data.time.nsec * 1e-9,
            seconds=data.time.sec,
            ns=data.time.nsec,
        )

    async def close(self, hard: bool = False):
        """ Stops the writer by closing the subscriber.

            args:
                hard (bool): If set to true the subscriber
                             buffer will be dropped and the file
                             will be immediately closed. Any data still
                             in the subscriber buffer will be lost.
        """
        await super().close(hard)
        self.log.info("Stopping TelData subscriber")
        await self._teldatasub.close(hard=False)
