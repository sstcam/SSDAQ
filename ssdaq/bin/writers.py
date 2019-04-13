from ssdaq.utils import common_args as cargs
from ssdaq.subscribers.slowsignal import SSFileWriter
from ssdaq.subscribers import writersubscriber


def writerfactory(descr,defaultport,writer):
    def writer():
        import argparse

        parser = argparse.ArgumentParser(
            description=descr,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        cargs.subport(parser, default=defaultport)
        cargs.subaddr(parser)
        cargs.filename(parser)
        cargs.version(parser)
        args = parser.parse_args()

        data_writer = writer(
            args.filename,
            file_enumerator="date",
            port=args.listen_port,
            ip=args.listen_interface,
        )

        data_writer.start()

        running = True
        while running:
            ans = input("To stop type `yes`: \n")
            if ans == "yes":
                running = False
        data_writer.close()
    return writer

slowsignal = writerfactory("Start a simple slow signal writer.",9996,SSFileWriter)
logwriter = writerfactory("Start a simple log data writer.",9998,writersubscriber.LogWriter)
timestampwriter = writerfactory("Start a simple timestamp data writer.",9999,writersubscriber.TimestampWriter)
triggerwriter = writerfactory("Start a simple trigger data writer.",9997,writersubscriber.TriggerWriter)
