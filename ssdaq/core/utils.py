import math
import asyncio
import sys
import inspect


def get_si_prefix(value: float) -> tuple:
    """Summary

    Args:
        value (float): Description

    Returns:
        tuple: Description
    """
    prefixes = [
        "a",
        "f",
        "p",
        "n",
        "μ",
        "m",
        "",
        "k",
        "M",
        "G",
        "T",
        "P",
        "E",
        "Z",
        "Y",
    ]
    if abs(value) < 1e-18:
        return 0, ""
    i = int(math.floor(math.log10(abs(value))))
    i = int(i / 3)
    p = math.pow(1000, i)
    s = round(value / p, 2)
    ind = i + 6
    #  if ind<0:
    #     ind = 0
    # if ind>14:
    #     ind=14
    return s, prefixes[ind]


def get_attritbues(obj_):
    """Summary

     Args:
         obj_ (TYPE): Description

     Returns:
         TYPE: Description
     """
    attributes = {}
    for attr in dir(obj_):
        if attr[0] == "_" or attr[:2] == "__":
            continue
        if inspect.ismethod(getattr(obj_, attr)) or inspect.isfunction(
            getattr(obj_, attr)
        ):
            continue
        attributes[attr] = getattr(obj_, attr)
    return attributes


def get_utc_timestamp()->(int,int):
    """Summary

    Returns:
        int, int
    """
    from datetime import datetime

    # from collections import namedtuple
    timestamp = datetime.utcnow().timestamp()
    s = int(timestamp)
    ns = int((timestamp - s) * 1e9)
    return s, ns


def async_loop_cleanup(loop):
    if hasattr(
        loop, "shutdown_asyncgens"
    ):  # This check is only needed for Python 3.5 and below
        loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


def async_shut_down_loop(loop):
    # Handle shutdown gracefully by waiting for all tasks to be cancelled
    tasks = asyncio.gather(
        *asyncio.Task.all_tasks(loop=loop), loop=loop, return_exceptions=True
    )
    tasks.add_done_callback(lambda t: loop.stop())
    tasks.cancel()

    # Keep the event loop running until it is either destroyed or all
    # tasks have really terminated
    while not tasks.done() and not loop.is_closed():
        loop.run_forever()


def async_interup_loop_cleanup(loop):

    # Optionally show a message if the shutdown may take a while
    # print("Attempting graceful shutdown, press Ctrl+C again to exit…", flush=True)

    # Do not show `asyncio.CancelledError` exceptions during shutdown
    # (a lot of these may be generated, skip this if you prefer to see them)
    def shutdown_exception_handler(loop, context):
        if "exception" not in context or not isinstance(
            context["exception"], asyncio.CancelledError
        ):
            loop.default_exception_handler(context)

    loop.set_exception_handler(shutdown_exception_handler)

    # Handle shutdown gracefully by waiting for all tasks to be cancelled
    tasks = asyncio.gather(
        *asyncio.Task.all_tasks(loop=loop), loop=loop, return_exceptions=True
    )
    tasks.add_done_callback(lambda t: loop.stop())
    tasks.cancel()

    # Keep the event loop running until it is either destroyed or all
    # tasks have really terminated
    while not tasks.done() and not loop.is_closed():
        loop.run_forever()


class AsyncPrompt:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.q = asyncio.Queue(loop=self.loop)
        self.loop.add_reader(sys.stdin, self.got_input)

    def got_input(self):
        asyncio.ensure_future(self.q.put(sys.stdin.readline()), loop=self.loop)

    async def __call__(self, msg, end="\n", flush=False):
        print(msg, end=end, flush=flush)
        return (await self.q.get()).rstrip("\n")
