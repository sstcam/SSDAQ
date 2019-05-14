from ssdaq.utils import common_args as cargs
from ssdaq import subscribers

# A writer-exectutable factory containing boilerplate code for the
# executable
def writerfactory(descr, defaultport, writer_cls):
    def writer():
        import argparse

        parser = argparse.ArgumentParser(
            description=descr, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        cargs.subport(parser, default=defaultport)
        cargs.subaddr(parser)
        cargs.filename(parser)
        cargs.version(parser)
        args = parser.parse_args()

        data_writer = writer_cls(
            args.filename, file_enumerator="date", port=args.sub_port, ip=args.sub_ip
        )

        data_writer.start()
        running = True
        while running:
            ans = input("To stop type `yes`: \n")
            if ans == "yes":
                running = False
        try:
            print("Waiting for writer to write buffered data to file......")
            print("`Ctrl-C` will empty the buffers and close the file immediately.")
            data_writer.close()
        except KeyboardInterrupt:
            print()
            data_writer.close(hard=True)

    return writer

#=================Threaded writer definitions======================
slowsignal = writerfactory(
    "Start a slow signal writer.", 9004, subscribers.SSFileWriter
)
logwriter = writerfactory(
    "Start a log data writer.", 9001, subscribers.LogWriter
)
timestampwriter = writerfactory(
    "Start a timestamp data writer.", 9003, subscribers.TimestampWriter
)
triggerwriter = writerfactory(
    "Start a trigger data writer.", 9002, subscribers.TriggerWriter
)


# A factory for an async writer-exectutable containing boilerplate code for the
# executable
def asyncwriterfactory(descr, defaultport, writer_cls):
    def writer():
        import argparse
        import asyncio

        parser = argparse.ArgumentParser(
            description=descr, formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        cargs.subport(parser, default=defaultport)
        cargs.subaddr(parser)
        cargs.filename(parser)
        cargs.version(parser)
        args = parser.parse_args()
        loop = asyncio.get_event_loop()
        data_writer = writer_cls(
            args.filename,
            file_enumerator="date",
            port=args.sub_port,
            ip=args.sub_ip,
            loop=loop,
        )
        from ssdaq.core.utils import (
            AsyncPrompt,
            async_interup_loop_cleanup,
            async_shut_down_loop,
        )

        async def control_input(loop, data_writer):
            running = True
            prompt = AsyncPrompt(loop)
            while running:
                try:
                    ans = await prompt("To stop type `yes`: \n")
                except asyncio.CancelledError:
                    print("Exit")
                    return
                if ans == "yes":
                    running = False
            print("Waiting for writer to write buffered data to file......", flush=True)
            print(
                "`Ctrl-C` will empty the buffers and close the file immediately.",
                flush=True,
            )
            close = loop.create_task(data_writer.close())
            close.add_done_callback(lambda x: loop.stop())

        task = loop.create_task(control_input(loop, data_writer))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print()
            if not task.cancelled():
                task.cancel()
            try:
                loop.run_until_complete(data_writer.close(True))
            except KeyboardInterrupt:
                print()
                async_interup_loop_cleanup(loop)

    return writer

#=================Asynchronous writer definitions======================
atriggerwriter = asyncwriterfactory(
    "Start a trigger data writer.", 9002, subscribers.ATriggerWriter
)

aslowsignal = asyncwriterfactory(
    "Start a slow signal writer.", 9004, subscribers.ASlowSignalWriter
)
