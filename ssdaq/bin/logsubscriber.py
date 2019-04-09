from ssdaq.subscribers import basicsubscriber
from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
import logging
import numpy as np

import argparse

import signal
from datetime import datetime
from ssdaq.core.logging import handlers

sh = logging.StreamHandler()
FORMAT = "%(asctime)s [%(levelname)-18s](%(pid)d)[$BOLD%(name)-20s$RESET]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
COLOR_FORMAT = handlers.formatter_message(FORMAT, True)
color_formatter = handlers.ColoredFormatter(COLOR_FORMAT)

sh.setFormatter(color_formatter)
def handle_log_record(log_record):
    """ Handles the incoming log record """

    logger = logging.getLogger(log_record.name)
    logger.propagate = False
    logger.addHandler(sh)
    for h in logger.handlers:
        h.setFormatter(color_formatter)
    logger.handle(log_record)

def main():

    parser = argparse.ArgumentParser(
        description="Subcribe to a published log stream.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l", dest="listen_port", type=int, default=5559, help="Subscription port"
    )
    parser.add_argument(
        "-i",
        dest="ip_addr",
        type=str,
        default="127.0.0.101",
        help="The ip/interface to subscribe to",
    )
    parser.add_argument(
        "-n",
        dest="n_readouts",
        type=int,
        default=None,
        help="the number of readouts to listen to before exiting (if not set there is no limit",
    )
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    sub = basicsubscriber.BasicLogSubscriber(port=args.listen_port, ip=args.ip_addr)
    sub.start()

    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    last_uc_ev = 0
    missed_counter = 0
    while True:
        try:
            record = sub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            sub.close()
            break
        if(record is not None):
            handle_log_record(record)
    sub.close()


if __name__ == "__main__":
    main()
