from ssdaq.utils import common_args as cargs
from ssdaq import subscribers


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
        running =True
        while running:
            ans = input("To stop type `yes`: \n")
            if ans == "yes":
                running = False
        try:
            print("Waiting for writer to write buffered data to file......")
            print("`Ctrl-C` will empty the buffers and close the file immediately.")
            data_writer.close()
        except KeyboardInterrupt:
            print()
            data_writer.close(hard=True)

    return writer


slowsignal = writerfactory(
    "Start a simple slow signal writer.", 9004, subscribers.SSFileWriter
)
logwriter = writerfactory(
    "Start a simple log data writer.", 9001, subscribers.LogWriter
)
timestampwriter = writerfactory(
    "Start a simple timestamp data writer.", 9003, subscribers.TimestampWriter
)
triggerwriter = writerfactory(
    "Start a simple trigger data writer.", 9002, subscribers.TriggerWriter
)
