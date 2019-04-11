#!/usr/bin/env python3


def main():
    from ssdaq import ZMQTCPPublisher
    from ssdaq.core.triggers import trigger_receiver
    import argparse
    from ssdaq.utils import common_args as cargs

    parser = argparse.ArgumentParser(
        description="Star a triggerpacket receiver.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l", dest="listen_port", type=int, default=2009, help="port for incoming data"
    )

    parser.add_argument(
        "-p",
        dest="publishing_port",
        type=int,
        default=5555,
        help="port for publishing data",
    )

    parser.add_argument(
        "-i",
        dest="publishing_interface",
        type=str,
        default="127.0.0.101",
        help="The publishing destination",
    )
    cargs.version(parser)
    cargs.verbosity(parser)
    from ssdaq import sslogger
    import logging

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    pub = ZMQTCPPublisher(port=args.publishing_port, ip=args.publishing_interface)
    trigserv = trigger_receiver.TriggerPacketReceiver(
        ip="0.0.0.0", port=args.listen_port, publishers=[pub]
    )

    trigserv.run()


if __name__ == "__main__":
    main()
