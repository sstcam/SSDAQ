from ssdaq.utils import common_args as cargs
from ssdaq.subscribers import writersubscriber


def logwriter():
    import argparse

    parser = argparse.ArgumentParser(
        description="Start a simple log data writer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    cargs.subport(parser, default=5559)
    cargs.subaddr(parser)
    cargs.filename(parser)
    cargs.version(parser)
    args = parser.parse_args()

    data_writer = writersubscriber.LogWriter(
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


def timestampwriter():
    import argparse

    parser = argparse.ArgumentParser(
        description="Start a simple timestamp data writer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    cargs.subport(parser, default=5559)
    cargs.subaddr(parser)
    cargs.filename(parser)
    cargs.version(parser)
    args = parser.parse_args()

    data_writer = writersubscriber.TimestampWriter(
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


def triggerwriter():
    import argparse

    parser = argparse.ArgumentParser(
        description="Start a simple trigger data writer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    cargs.subport(parser, default=5559)
    cargs.subaddr(parser)
    cargs.filename(parser)
    cargs.version(parser)
    args = parser.parse_args()

    data_writer = writersubscriber.TriggerWriter(
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


if __name__ == "__main__":
    logwriter()
