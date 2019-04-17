from ssdaq.utils import common_args as cargs
from ssdaq.subscribers.slowsignal import SSFileWriter
from ssdaq.subscribers import writersubscriber


def writerfactory(descr, defaultport, writer_cls):
    def writer():
        import argparse

        parser = argparse.ArgumentParser(
            description=descr, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        cargs.subport(parser, default=defaultport)
        cargs.subaddr(parser)
        cargs.filename(parser)
        cargs.version(parser)
        args = parser.parse_args()

        data_writer = writer_cls(
            args.filename, file_enumerator="date", port=args.sub_port, ip=args.sub_ip
        )

        data_writer.start()

        running = True
        while running:
            ans = input("To stop type `yes`: \n")
            if ans == "yes":
                running = False
        data_writer.close()

    return writer


slowsignal = writerfactory("Start a simple slow signal writer.", 9004, SSFileWriter)
logwriter = writerfactory(
    "Start a simple log data writer.", 9001, writersubscriber.LogWriter
)
timestampwriter = writerfactory(
    "Start a simple timestamp data writer.", 9003, writersubscriber.TimestampWriter
)
triggerwriter = writerfactory(
    "Start a simple trigger data writer.", 9002, writersubscriber.TriggerWriter
)
