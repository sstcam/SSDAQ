from ssdaq.subscribers import basicsubscriber
from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
import logging
import numpy as np

import argparse

import signal
from datetime import datetime
import time


def main():

    parser = argparse.ArgumentParser(
        description="Subcribe to a published trigger packet stream.",
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

    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    last_uc_ev = 0
    missed_counter = 0
    time1 = time.time()
    time2 = time.time()
    while True:
        try:
            trigger = sub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            sub.close()
            break

        if trigger is not None:
            if last_uc_ev != 0 and last_uc_ev + 1 != trigger.uc_ev:
                missed_counter += 1

            print("##################################")
            print("#Data: {}".format(trigger.__class__.__name__))
            for name, value in trigger._asdict().items():
                print("#    {}: {}".format(name, value))
            print("#    Missed: {}".format(missed_counter))
            print("#    Frequency: {} Hz".format(1.0 / ((time2 - time1) + 1e-7)))
            print("#    dt: {} s".format(time2 - time1))
            # print("#    t: {} {} s".format(time2,time1))
            print("##################################")
            time1 = time2
            time2 = time.time()

            last_uc_ev = trigger.uc_ev
    sub.close()
    sub.join()


if __name__ == "__main__":
    main()
