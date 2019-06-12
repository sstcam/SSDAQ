from ssdaq import subscribers
from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
from ssdaq import data
import logging
import numpy as np
import argparse
import signal
from datetime import datetime
import time
from statistics import mean


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
        m = ~np.isnan(readout.data)
        print("Participating TMs: ", set(np.where(m)[0]))
        print("Number of participating TMs: ", len(set(np.where(m)[0])))
        print("Amplitude sum: {} mV".format(np.nansum(readout.data.flatten())))
        # print(readout.data)
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

    #    plt.figure()
    #    plt.hist(n_modules_per_readout, 10, facecolor="g", alpha=0.75)
    #    plt.show()
    rsub.close()
    rsub.join()


def timestampdump():
    def isValidTS(ts):
        if ts.time.HasField("seconds") and ts.time.HasField("pico_seconds"):
            return True
        else:
            return False

    def isSmaller(ts_last, ts_current):
        if (ts_last.time.seconds * 1e12 + ts_last.time.pico_seconds) <= (
            ts_current.time.seconds * 1e12 + ts_current.time.pico_seconds
        ):
            return True
        else:
            return False

    def get_deltat_in_ps(ts_last, ts_current):
        tlast = ts_last.time.seconds * 1e12 + ts_last.time.pico_seconds
        tcurr = ts_current.time.seconds * 1e12 + ts_current.time.pico_seconds
        return tcurr - tlast

    # myStats = {"fTrigger":0, "fCurrent_ts":data.TriggerMessage(), "fLast_ts":data.TriggerMessage()}
    def add_timestamp(ts, myStats):
        myStats["fTrigger"] += 1
        myStats["fCurrent_ts"] = ts
        if not isValidTS(myStats["fLast_ts"]):
            myStats["fLast_ts"] = ts

    def get_frequency_in_Hz(myStats):
        if not (
            myStats["fTrigger"]
            or isValidTS(myStats["fLast_ts"])
            or isValidTS(myStats["fCurrent_ts"])
        ):
            return
        delt = get_deltat_in_ps(myStats["fLast_ts"], myStats["fCurrent_ts"]) * 1e-12
        trig = myStats["fTrigger"]
        myStats["fTrigger"] = 0
        myStats["fLast_ts"] = myStats["fCurrent_ts"]
        if delt <= 1e-12:
            return
        else:
            return trig / delt

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

    readout_stats = {
        "fTrigger": 0,
        "fCurrent_ts": data.TriggerMessage(),
        "fLast_ts": data.TriggerMessage(),
    }
    readout_counter_missed = 0
    readout_counter_last = 0
    readout_ts_smaller = 0
    readout_freq = []

    busy_stats = {
        "fTrigger": 0,
        "fCurrent_ts": data.TriggerMessage(),
        "fLast_ts": data.TriggerMessage(),
    }
    busy_counter_missed = 0
    busy_counter_last = 0
    busy_ts_smaller = 0
    busy_freq = []

    while True:
        try:
            tmsg = sub.get_data()
        except KeyboardInterrupt:
            print("\nClosing listener")
            sub.close()
            break

        if tmsg is not None:
            # print(tmsg.type,tmsg.event_counter)
            # print(tmsg.time.seconds, tmsg.time.pico_seconds)

            if tmsg.type == 1:  # readout triggers only
                add_timestamp(tmsg, readout_stats)

                # check if events count up properly
                current_readout_counter = tmsg.event_counter
                if (
                    readout_counter_last != 0
                    and readout_counter_last + 1 != current_readout_counter
                ):
                    readout_counter_missed += 1
                    print("# of missed readout events", readout_counter_missed)
                readout_counter_last = current_readout_counter

                # check for timing issues within the time stamps
                if isSmaller(readout_stats["fLast_ts"], readout_stats["fCurrent_ts"]):
                    readout_ts_smaller += 1
                    print("# of readout timestamps smaller", readout_ts_smaller)

                # try something useful
                updatetime = 1  # how other do we want to calculate the frequency
                if (
                    get_deltat_in_ps(
                        readout_stats["fLast_ts"], readout_stats["fCurrent_ts"]
                    )
                    * 1e12
                ) > updatetime:
                    readout_frequency = get_frequency_in_Hz(readout_stats)
                    readout_freq.append(readout_frequency)
                    print("> Readout Frequency [Hz] =", readout_frequency)

            if tmsg.type == 2:  # busy triggers (same logic as readout stuff)
                add_timestamp(tmsg, busy_stats)

                current_busy_counter = tmsg.event_counter
                if (
                    busy_counter_last != 0
                    and busy_counter_last + 1 != current_busy_counter
                ):
                    busy_counter_missed += 1
                    print("# of missed busy events", busy_counter_missed)
                busy_counter_last = current_busy_counter

                if isSmaller(busy_stats["fLast_ts"], busy_stats["fCurrent_ts"]):
                    busy_ts_smaller += 1
                    print("# of busy timestamps smaller", busy_ts_smaller)

                updatetime = 1
                if (
                    get_deltat_in_ps(busy_stats["fLast_ts"], busy_stats["fCurrent_ts"])
                    * 1e12
                ) > updatetime:
                    busy_frequency = get_frequency_in_Hz(busy_stats)
                    busy_freq.append(busy_frequency)
                    print("> Busy Frequency [Hz] =", busy_frequency)

    """
    try:
        from matplotlib import pyplot as plt
    except ImportError:
        return

    plt.figure()
    plt.hist(readout_freq, 100, facecolor="g", alpha=0.75)
    plt.figtext(0.1,0.9,mean(readout_freq))
    plt.show()
    """

    sub.close()
    sub.join()


from ssdaq.core.utils import get_si_prefix


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
    last = 0
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
            now = trigger.TACK
            print("##################################")
            print("#Data: {}".format(trigger.__class__.__name__))
            for name, value in trigger._asdict().items():

                if name == "trigg_union":  # or name == 'trigg'
                    print("#    {}: {}".format(name, np.where(value)[0]))
                elif name == "trigg":
                    # tr = trigger._trigger_phases
                    # for i, t in enumerate(tr):
                    #     print(i,hex(t))
                    # print("#    {}: {}".format(name, tr[tr>0]))
                    # print("#    {}: {}".format(name, np.where(tr>0)[0]))
                    print("#    {}: {}".format(name, np.where(value)[0]))
                    # print("#    {}: {}".format(name, value))
                elif name == "trigg_phase":
                    print("#    {}: {}".format(name, 7 - int(np.log2(value))))
                else:
                    print("#    {}: {}".format(name, value))

            print("#    Missed: {}".format(missed_counter))
            print(
                "#    Frequency: {} {}Hz".format(
                    *get_si_prefix(1.0 / ((now - last) * 1e-9))
                )
            )
            print("#    dt: {} s".format((now - last) * 1e-9))
            print("##################################")
            last = now
            last_uc_ev = trigger.uc_ev
    sub.close()
    sub.join()


from ssdaq import logging as ch_logging

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
    logger.handlers = []


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
        # print(record)
        if record is not None:
            handle_log_record(record)
    # sub.close()


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
