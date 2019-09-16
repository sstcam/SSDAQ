from ssdaq.utils import common_args as cargs

import argparse

import signal
from datetime import datetime
from blessed import Terminal
from ssdaq import subscribers
from ssdaq.core.utils import get_si_prefix
from ssdaq import sslogger
import logging


class ReceiverStatusDash:
    def __init__(self, terminal, name, loc):
        self.terminal = terminal
        self.loc = loc
        self.name = name
        self.status = False
        self.counter = 0
        self.last_seen = datetime.now().timestamp()
        self.last_mon = None

    def render(self, mon):
        # print(mon.reciver.name,self.name,mon.reciver.name!=self.name)

        if mon is None or mon.reciver.name != self.name:
            if datetime.now().timestamp() - self.last_seen > 1.5:
                mon = None
            else:
                return
        self.last_seen = datetime.now().timestamp()
        # print(mon.reciver.name,self.name)

        if mon is None:
            status = self.terminal.bold_red("Offline  ")
        else:
            status = self.terminal.bold_green("Online  ")

        if mon is not None and mon.reciver.recv_data:
            data = self.terminal.bold_green("YES")
            val, p = get_si_prefix(mon.reciver.data_rate)
            rate = "%.3g %sHz     " % (val, p)  # mon.reciver.data_rate
        else:
            data = self.terminal.bold_red("No ")
            rate = "---      "

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
        self.last_mon = mon


import queue


def mondumper1():

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

    sub = subscribers.BasicMonSubscriber(port=args.sub_port, ip=args.sub_ip)
    sub.start()

    signal.alarm(0)
    print("Press `ctrl-C` to stop")

    rdash = ReceiverStatusDash(t, "ReadoutAssembler", (0, 1))
    triggdash = ReceiverStatusDash(t, "TriggerPacketReceiver", (30, 1))
    timedash = ReceiverStatusDash(t, "TimestampReceiver", (0, 6))
    logdash = ReceiverStatusDash(t, "LogReceiver", (30, 6))
    mondash = ReceiverStatusDash(t, "MonitorReceiver", (0, 11))
    teldash = ReceiverStatusDash(t, "TelDataReceiver", (30, 11))
    rtcamim = ReceiverStatusDash(t, "RTCameraImagePublisher", (0, 17))
    dashes = [rdash, timedash, triggdash, logdash, mondash, teldash, rtcamim]

    with t.fullscreen():
        oldh = t.height
        oldw = t.width
        while True:
            try:
                mon = sub.get_data(timeout=1.0)
            except queue.Empty:
                mon = None
            except KeyboardInterrupt:
                print("\nClosing listener")
                sub.close()
                break
            if t.height != oldh or t.width != oldw:
                oldh = t.height
                oldw = t.width
                t.clear()
                for dash in dashes:
                    dash.render(dash.last_mon)
            for dash in dashes:
                dash.render(mon)
        sub.close()


def mondumper():
    import curses
    import asyncio
    from ssdaq.core.utils import (
        AsyncPrompt,
        async_interup_loop_cleanup,
        async_shut_down_loop,
    )

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
    #    stdscr = curses.initscr()
    #    curses.noecho()
    #    curses.cbreak()

    t = Terminal()

    sub = subscribers.AsyncMonSubscriber(port=args.sub_port, ip=args.sub_ip)
    loop = asyncio.get_event_loop()
    # sub.start()

    print("Press `ctrl-C` to stop")

    rdash = ReceiverStatusDash(t, "ReadoutAssembler", (0, 1))
    triggdash = ReceiverStatusDash(t, "TriggerPacketReceiver", (30, 1))
    timedash = ReceiverStatusDash(t, "TimestampReceiver", (0, 6))
    logdash = ReceiverStatusDash(t, "LogReceiver", (30, 6))
    mondash = ReceiverStatusDash(t, "MonitorReceiver", (0, 11))
    teldash = ReceiverStatusDash(t, "TelDataReceiver", (30, 11))
    rtcamim = ReceiverStatusDash(t, "RTCameraImage", (0, 16))
    dashes = [rdash, timedash, triggdash, logdash, mondash, teldash, rtcamim]

    async def control_task(loop, dashes, sub, t):
        prompt = AsyncPrompt(loop)
        oldh = t.height
        oldw = t.width
        while True:
            try:
                mon = await asyncio.wait_for(sub.get_data(), 1.0)
            except asyncio.TimeoutError:
                mon = None
            #               sslogger.warn("{},{}".format(t.height,t.width))
            if t.height != oldh or t.width != oldw:
                oldh = t.height
                oldw = t.width
                print(t.clear())
                for dash in dashes:
                    dash.render(dash.last_mon)
            #                    sslogger.error("HERE")

            for dash in dashes:
                dash.render(mon)
        # stdscr.refresh()

    with t.fullscreen():

        main_task = loop.create_task(control_task(loop, dashes, sub, t))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            # print('HERE')
            # klakslkd

            # curses.echo()
            loop.run_until_complete(sub.close())
        # finally:
        #    stdscr.keypad(0)
        #    curses.echo()
        #    curses.endwin()


# from . import dashing
# class ReceiverStatusTile(dashing.Tile):
#     def __init__(self,  name ,**kw):
#         super(ReceiverStatusTile, self).__init__(**kw)
#         self.name = name
#         self.status = False
#         self.counter = 0
#         self.last_seen = datetime.now().timestamp()
#         self.last_mon = None
#         self.mon = None
#     def set_mon(self,)
#         if self.mon is None or self.mon.reciver.name != self.name:
#             if datetime.now().timestamp() - self.last_seen > 1.5:
#                 self.mon = None
#         self.last_seen = datetime.now().timestamp()
#     def _display(self, tbox, parent):
#         # print(mon.reciver.name,self.name,mon.reciver.name!=self.name)
#         if self.mon is None:
#             return
#         tbox = self._draw_borders_and_title(tbox)

#         if self.mon is None:
#             status = self.terminal.bold_red("Offline  ")
#         else:
#             status = self.terminal.bold_green("Online  ")

#         if self.mon is not None and self.mon.reciver.recv_data:
#             data = self.terminal.bold_green("YES")
#             val, p = get_si_prefix(self.mon.reciver.data_rate)
#             rate = "%.3g %sHz     " % (val, p)  # self.mon.reciver.data_rate
#         else:
#             data = self.terminal.bold_red("No ")
#             rate = "---      "

#         with self.terminal.location(self.loc[0], self.loc[1]):
#             print(
#                 self.terminal.bold("Receiver: ") + self.terminal.bold_white(self.name)
#             )
#         with self.terminal.location(self.loc[0], self.loc[1] + 1):
#             print(self.terminal.bold("Status: ") + status)
#         with self.terminal.location(self.loc[0], self.loc[1] + 2):
#             print(self.terminal.bold("Receving data: ") + data)
#         with self.terminal.location(self.loc[0], self.loc[1] + 3):
#             print(
#                 self.terminal.bold("Data rate: ")
#                 + self.terminal.bold_magenta("%s" % rate)
#             )
#         self.counter += 1
#         self.last_mon = self.mon

# def mondumper3():
#     import curses
#     import asyncio
#     from ssdaq.core.utils import (
#             AsyncPrompt,
#             async_interup_loop_cleanup,
#             async_shut_down_loop,
#         )

#     parser = argparse.ArgumentParser(
#         description="Subcribe to a published log stream.",
#         formatter_class=argparse.ArgumentDefaultsHelpFormatter,
#     )
#     cargs.subport(parser, default=9005)
#     cargs.subaddr(parser)
#     cargs.verbosity(parser)
#     cargs.version(parser)

#     args = parser.parse_args()
#     eval("sslogger.setLevel(logging.%s)" % args.verbose)
# #    stdscr = curses.initscr()
# #    curses.noecho()
# #    curses.cbreak()

#     t = Terminal()

#     sub = subscribers.AsyncMonSubscriber(port=args.sub_port, ip=args.sub_ip)
#     loop = asyncio.get_event_loop()
#     # sub.start()

#     print("Press `ctrl-C` to stop")

#     main = HSplit()

#     rdash = ReceiverStatusDash(t, "ReadoutAssembler", (0, 1))
#     triggdash = ReceiverStatusDash(t, "TriggerPacketReceiver", (30, 1))
#     timedash = ReceiverStatusDash(t, "TimestampReceiver", (0, 6))
#     logdash = ReceiverStatusDash(t, "LogReceiver", (30, 6))
#     mondash = ReceiverStatusDash(t, "MonitorReceiver", (0, 11))
#     teldash = ReceiverStatusDash(t, "TelDataReceiver", (30, 11))
#     rtcamim = ReceiverStatusDash(t, "RTCameraImage", (0, 16))
#     dashes = [rdash, timedash, triggdash, logdash, mondash, teldash,rtcamim]


#     async def control_task(loop,dashes,sub,t):
#             prompt = AsyncPrompt(loop)
#             oldh = t.height
#             oldw = t.width
#             while True:
#                 try:
#                     mon = await asyncio.wait_for(sub.get_data(),1.0)
#                 except asyncio.TimeoutError:
#                     mon = None
#  #               sslogger.warn("{},{}".format(t.height,t.width))
#                 if t.height!=oldh or t.width!=oldw:
#                     oldh = t.height
#                     oldw = t.width
#                     print(t.clear())
#                     for dash in dashes:
#                         dash.render(dash.last_mon)
# #                    sslogger.error("HERE")

#                 for dash in dashes:
#                     dash.render(mon)
#             #stdscr.refresh()
#     with t.fullscreen():

#         main_task = loop.create_task(control_task(loop, dashes,sub,t))
#         try:
#             loop.run_forever()
#         except KeyboardInterrupt:
#             # print('HERE')
#             # klakslkd

#            # curses.echo()
#             loop.run_until_complete(sub.close())
#         #finally:
#         #    stdscr.keypad(0)
#         #    curses.echo()
#         #    curses.endwin()
if __name__ == "__main__":
    mondumper()
