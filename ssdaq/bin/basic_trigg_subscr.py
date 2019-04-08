from ssdaq.subscribers import basicsubscriber
from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
import logging
import numpy as np

import argparse

import signal
from datetime import datetime


def main():

    parser = argparse.ArgumentParser(
        description="Start a simple Slow Signal readout listener.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l", dest="listen_port", type=int, default=5555, help="Subscription port"
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

    sub = basicsubscriber.BasicTriggerSubscriber(port=args.listen_port, ip=args.ip_addr)
    sub.start()

    readout_counter = np.zeros(32)
    n_modules_per_readout = []
    n = 0
    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    while True:
        try:
            trigger = sub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            sub.close()
            break
        if trigger is not None:
            print("##################################")
            print("#Trigger: {}".format(trigger.__class__.__name__))
            for name, value in trigger._asdict().items():
                print("#    {}: {}".format(name, value))
            print("##################################")

    sub.close()
    sub.join()


if __name__ == "__main__":
    main()
