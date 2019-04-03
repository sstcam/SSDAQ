from ssdaq.receivers.slowsignal import SSFileWriter
from ssdaq.utils import common_args as cargs


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Start a simple event data writer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l",
        dest="listen_port",
        type=str,
        default="5555",
        help="port for incoming event data",
    )

    parser.add_argument(
        "-i",
        dest="listen_interface",
        type=str,
        default="127.0.0.101",
        help="port for incoming event data",
    )

    parser.add_argument("filename", type=str, default="5555", help="Output file name")

    cargs.version(parser)
    args = parser.parse_args()

    data_writer = SSFileWriter(
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
    main()
