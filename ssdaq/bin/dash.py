from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
import logging
import numpy as np

import argparse

import signal
from datetime import datetime
import time
from blessed import Terminal
from ssdaq.subscribers import basicsubscriber


class ReceiverStatusDash:
    def __init__(self, terminal, name, loc):
        self.terminal = terminal
        self.loc = loc
        self.name = name
        self.status = False
        self.counter = 0
        self.last_seen = datetime.now().timestamp()

    def render(self, mon):
        # print(mon.reciver.name,self.name,mon.reciver.name!=self.name)

        if mon.reciver.name != self.name:
            if datetime.now().timestamp() - self.last_seen > 1.5:
                mon = None
            else:
                return
        self.last_seen = datetime.now().timestamp()
        # print(mon.reciver.name,self.name)

        if mon is None:
            status = self.terminal.bold_red("Offline")
        else:
            status = self.terminal.bold_green("Online")

        if mon is not None and mon.reciver.recv_data:
            data = self.terminal.bold_green("YES")
            rate = "%.3g    " % mon.reciver.data_rate
        else:
            data = self.terminal.bold_red("No ")
            rate = "---"

        with self.terminal.location(self.loc[0], self.loc[1]):
            print(
                self.terminal.bold("Receiver: ") + self.terminal.bold_white(self.name)
            )
        with self.terminal.location(self.loc[0], self.loc[1] + 1):
            print(self.terminal.bold("Status: ") + status)
        with self.terminal.location(self.loc[0], self.loc[1] + 2):
            print(self.terminal.bold("Receving data: ") + data)
        with self.terminal.location(self.loc[0], self.loc[1] + 3):
            print(
                self.terminal.bold("Data rate: ")
                + self.terminal.bold_magenta("%s" % rate)
            )
        self.counter += 1


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

    t = Terminal()

    sub = basicsubscriber.BasicMonSubscriber(port=args.sub_port, ip=args.sub_ip)
    sub.start()

    signal.alarm(0)
    print("Press `ctrl-C` to stop")
    last_uc_ev = 0
    missed_counter = 0

    rdash = ReceiverStatusDash(t, "SSReadoutAssembler", (0, 1))
    triggdash = ReceiverStatusDash(t, "TriggerPacketReceiver", (30, 1))
    timedash = ReceiverStatusDash(t, "TimestampReceiver", (0, 6))
    logdash = ReceiverStatusDash(t, "LogReceiver", (30, 6))
    mondash = ReceiverStatusDash(t, "MonitorReceiver", (0, 12))
    dashes = [rdash, timedash, triggdash, logdash,mondash]
    with t.fullscreen():
        while True:
            try:
                mon = sub.get_data()
            except KeyboardInterrupt:
                print("\nClosing listener")
                sub.close()
                break
            if mon is not None:
                # print(mon)
                for dash in dashes:
                    dash.render(mon)
        sub.close()


if __name__ == "__main__":
    mondumper()
#

# sub = basicsubscriber.BasicMonSubscriber(port=args.sub_port, ip=args.sub_ip)


#     with t.location(0, 1):
#         print(t.bold("Hi there!"))
#         print(t.bold_red_on_bright_green("It hurts my eyes!"))

#     with t.location(0, t.height - 1):
#         print(t.center(t.bold("press any key to continue.")))

#     with t.cbreak():
#         inp = t.inkey()

#     # print('You pressed ' + repr(inp))
#     # t.exit_fullscreen

#     loop = asyncio.get_event_loop()
#     loop.create_task(getinput(loop))
#     loop.create_task(counter2(t, 0.0001))
#     loop.create_task(counter(t, 1))

#     try:
#         loop.run_forever()
#     except Exception as e:
#         print(e)
