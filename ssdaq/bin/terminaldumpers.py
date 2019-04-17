from ssdaq import subscribers
from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
import logging
import numpy as np
import argparse
import signal
from datetime import datetime
import time


def slowsignaldump():

    parser = argparse.ArgumentParser(
        description="Start a simple Slow Signal readout listener.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.n_outputs(parser)
    cargs.subport(parser, default=9004)
    cargs.subaddr(parser)
    parser.add_argument(
        "-t",
        dest="tm_numb",
        nargs="?",
        type=int,
        help="Set target module number for which SS data is printed out",
    )

    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    rsub = subscribers.SSReadoutSubscriber(port=args.sub_port, ip=args.sub_ip)
    rsub.start()

    readout_counter = np.zeros(32)
    n_modules_per_readout = []
    n = 0
    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    while True:
        try:
            readout = rsub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            rsub.close()
            break
        # if(n>0):
        #     print('\033[7   A ')
        print("Readout number %d" % (readout.iro))
        print("Timestamp %d ns" % (readout.time))
        print("Timestamp %f s" % (readout.time * 1e-9))
        print("Cpu timestamp {}".format(datetime.utcfromtimestamp(readout.cpu_t)))
        print("Cpu timestamp {}".format(readout.cpu_t))
        print("Cpu timestamp {}".format(readout.cpu_t_s))
        print("Cpu timestamp {}".format(readout.cpu_t_ns))
        # print(np.where(m)[0])
        # n_modules_per_readout.append(np.sum(m))
        # readout_counter[m] += 1
        # m = readout_counter>0

        if args.tm_numb:
            print(readout.data[args.tm_numb])
        n += 1
        if args.n_outputs != None and n >= args.n_outputs:
            break

    try:
        from matplotlib import pyplot as plt
    except ImportError:
        return

    plt.figure()
    plt.hist(n_modules_per_readout, 10, facecolor="g", alpha=0.75)
    plt.show()
    rsub.close()
    rsub.join()


def timestampdump():

    parser = argparse.ArgumentParser(
        description="Subcribe to a published timestamp stream.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.subport(parser, default=9003)
    cargs.subaddr(parser)
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    sub = subscribers.BasicTimestampSubscriber(port=args.sub_port, ip=args.sub_ip)
    sub.start()

    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    last_uc_ev = 0
    missed_counter = 0
    time1 = time.time()
    time2 = time.time()
    while True:
        try:
            tmsg = sub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            sub.close()
            break

        if tmsg is not None and tmsg.type == 1:

            # if last_uc_ev != 0 and last_uc_ev + 1 != trigger.uc_ev:
            #     missed_counter += 1

            print("##################################")
            # print("#Data: {}".format(trigger.__class__.__name__))
            # for name, value in trigger._asdict().items():
            #     print("#    {}: {}".format(name, value))
            print("# {}".format(tmsg))
            # print("#    Missed: {}".format(missed_counter))
            print("#    Frequency: {} Hz".format(1.0 / ((time2 - time1) + 1e-7)))
            print("#    dt: {} s".format(time2 - time1))
            print("##################################")
            time1 = time2
            time2 = time.time()

            # last_uc_ev = trigger.uc_ev
    sub.close()
    sub.join()


def triggerdump():

    parser = argparse.ArgumentParser(
        description="Subcribe to a published trigger packet stream.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.subport(parser, default=9002)
    cargs.subaddr(parser)
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    sub = subscribers.BasicTriggerSubscriber(port=args.sub_port, ip=args.sub_ip)
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


from ssdaq.core import logging as ch_logging

sh = logging.StreamHandler()
FORMAT = "%(asctime)s [%(levelname)-18s](%(pid)d)[$BOLD%(name)-20s$RESET]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
COLOR_FORMAT = ch_logging.formatter_message(FORMAT, True)
color_formatter = ch_logging.ColoredFormatter(COLOR_FORMAT)

sh.setFormatter(color_formatter)


def handle_log_record(log_record):
    """ Handles the incoming log record """

    logger = logging.getLogger(log_record.name)
    logger.propagate = False
    logger.addHandler(sh)
    for h in logger.handlers:
        h.setFormatter(color_formatter)
    logger.handle(log_record)


def logdump():

    parser = argparse.ArgumentParser(
        description="Subcribe to a published log stream.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.subport(parser, default=9001)
    cargs.subaddr(parser)
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    sub = subscribers.BasicLogSubscriber(port=args.sub_port, ip=args.sub_ip)
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
        if record is not None:
            handle_log_record(record)
    sub.close()


def mondumper():

    parser = argparse.ArgumentParser(
        description="Subcribe to a published log stream.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cargs.subport(parser, default=9005)
    cargs.subaddr(parser)
    cargs.verbosity(parser)
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)" % args.verbose)

    sub = subscribers.BasicMonSubscriber(port=args.sub_port, ip=args.sub_ip)
    sub.start()

    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    last_uc_ev = 0
    missed_counter = 0
    while True:
        try:
            mon = sub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            sub.close()
            break
        if mon is not None:
            print(mon)
    sub.close()
