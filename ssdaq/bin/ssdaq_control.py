from ssdaq.utils import daemon
import ssdaq
from ssdaq.core import publishers
from ssdaq import sslogger, subscribers

from ssdaq import logging as handlers
import os
from pathlib import Path
import logging

sslogger.addHandler(handlers.ChecSocketLogHandler("127.0.0.1", 10001))
signal_counter = 0


class FileWriterDaemonWrapper(daemon.Daemon):
    def __init__(
        self, name, writer_cls, stdout="/dev/null", stderr="/dev/null", **kwargs
    ):
        # Deamonizing the server
        daemon.Daemon.__init__(
            self, "/tmp/{}.pid".format(name), stdout=stdout, stderr=stderr
        )
        self.kwargs = kwargs
        self.writer_cls = writer_cls
        self.name = name

    def run(self):
        import signal

        data_writer = self.writer_cls(name=self.name, **self.kwargs)
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

        async def shutdown(signal, loop):
            data_writer.log.info(f"Received exit signal {signal.name}...")
            data_writer.log.info("Closing file handlers")
            done = loop.create_task(data_writer.close())
            await done
            # tasks = [t for t in asyncio.all_tasks() if t is not
            #         asyncio.current_task()]

            # [task.cancel() for task in tasks]

            # data_writer.log.info('Canceling outstanding tasks')
            # await asyncio.gather(*tasks)
            loop.stop()
            data_writer.log.info("Shutdown complete.")

        for s in signals:
            data_writer.loop.add_signal_handler(
                s,
                lambda s=s: data_writer.loop.create_task(shutdown(s, data_writer.loop)),
            )

        data_writer.loop.run_forever()


class RecieverDaemonWrapper(daemon.Daemon):
    def __init__(
        self,
        receiver_cls,
        stdout="/dev/null",
        stderr="/dev/null",
        set_taskset=False,
        core_id=0,
        log_level="INFO",
        **kwargs,
    ):
        # Deamonizing the server
        daemon.Daemon.__init__(
            self,
            "/tmp/{}_daemon.pid".format(receiver_cls.__name__),
            stdout=stdout,
            stderr=stderr,
        )
        self.receiver_cls = receiver_cls
        self.kwargs = kwargs
        self.set_taskset = set_taskset
        self.core_id = str(core_id)

        eval("sslogger.setLevel(logging.%s)" % log_level)
        sslogger.info("Set logging level to {}".format(log_level))

    def run(self):
        from subprocess import call
        import os

        if self.set_taskset:
            # forces the process to one particular CPU core
            call(["taskset", "-cp", self.core_id, "%s" % (str(os.getpid()))])
        eps = []
        i = 1
        for epname, epconf in self.kwargs["Publishers"].items():
            epconf["name"] = epname
            pubclass = getattr(publishers, epconf["class"])
            del epconf["class"]
            eps.append(pubclass(**epconf))
            i += 1
        reciever = self.receiver_cls(publishers=eps, **self.kwargs["Receiver"])
        reciever.run()


import yaml
import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class MyGroup(click.Group):
    def parse_args(self, ctx, args):
        if args[0] in self.commands:
            if len(args) == 1 or args[1] not in self.commands:
                args.insert(0, "")
        super(MyGroup, self).parse_args(ctx, args)


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(ssdaq.__version__)
    ctx.exit()


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version",
    callback=print_version,
    expose_value=False,
    is_eager=True,
)
def cli(ctx):
    """Start, stop and control receiver and writer daemons"""
    ctx.ensure_object(dict)

    from pkg_resources import resource_stream  # , resource_string, resource_listdir

    ctx.obj["CONFIG"] = yaml.safe_load(
        resource_stream("ssdaq.resources", "ssdaq-default-config.yaml")
    )
    ctx.obj["DAQCONFIG"] = yaml.safe_load(
        resource_stream("ssdaq.resources", "ssdaq-default-daq-config.yaml")
    )

    if os.path.isfile(os.path.join(Path.home(), ".ssdaq_config.yaml")):
        conf = yaml.safe_load(
            open(os.path.join(Path.home(), ".ssdaq_config.yaml"), "r")
        )
        if "writer-config" in conf:
            if not os.path.isfile(conf["writer-config"]):
                sslogger.warn(
                    "custom writer-config file not found falling back to the default"
                )
            else:
                sslogger.info(
                    "loading custom writer config from {}".format(conf["writer-config"])
                )
                ctx.obj["CONFIG"] = yaml.safe_load(open(conf["writer-config"], "r"))
        if "daq-config" in conf:
            if not os.path.isfile(conf["daq-config"]):
                sslogger.warn(
                    "custom daq-config file not found falling back to the default"
                )
            else:
                ctx.obj["DAQCONFIG"] = yaml.safe_load(open(conf["daq-config"], "r"))
                sslogger.info(
                    "loading custom DAQ config from {}".format(conf["daq-config"])
                )


@click.group()
@click.pass_context
def start(ctx):  # ,config):
    """Start receivers or data writers """
    ctx.ensure_object(dict)


@start.command()
@click.option("--daemon/--no-daemon", "-d", default=False, help="run as daemon")
@click.option("--config", "-c", default=None, help="specify custom config file")
@click.option("--list", "-l", "ls", is_flag=True, help="list possible writers")
@click.argument("components", nargs=-1)
@click.option(
    "--filename-prefix",
    "-f",
    default=None,
    help="Set filename prefix (over-rides the loaded configuration). Can only be used when starting a single writer",
)
@click.option(
    "--output-folder",
    "-o",
    default=None,
    help="Set output folder (over-rides the loaded configuration)",
)
@click.pass_context
def dw(ctx, filename_prefix, output_folder, daemon, components, config, ls):
    """Start a data writer with an optional custom CONFIG file"""
    if config:
        ctx.obj["CONFIG"] = yaml.safe_load(open(config, "r"))
    config = ctx.obj["CONFIG"]
    if ls:
        for k, v in config.items():
            print("`{}` as class: {}".format(k, v["Writer"]["class"]))
        exit()

    components = list(components)
    cmptlen = len(components)
    if cmptlen > 1 and not daemon:
        print("Can only start multiple writers with `-d` option...")
        exit()

    if filename_prefix and cmptlen > 1:
        print(
            "Setting same file name prefix for multiple writers does not make sense...."
        )
        exit()
    for compt, comp_config in config.items():
        if cmptlen == 0 or (cmptlen > 0 and foundcmp(compt, components)):
            writer = getattr(subscribers, comp_config["Writer"]["class"])
            class_ = comp_config["Writer"]["class"]
            del comp_config["Writer"]["class"]

            if filename_prefix:
                comp_config["Writer"]["file_prefix"] = filename_prefix
            if output_folder:
                comp_config["Writer"]["folder"] = output_folder

            print("Starting {} writer...".format(class_))
            writerdaemon = FileWriterDaemonWrapper(
                compt, writer, **comp_config["Daemon"], **comp_config["Writer"]
            )
            writerdaemon.start(daemon)
    # if not started:


def load_config(ctx, config):
    if config:
        ctx.obj["DAQCONFIG"] = yaml.safe_load(open(config, "r"))
    return ctx.obj["DAQCONFIG"]


def daq_start(config, components):
    cmptlen = len(components)
    for compt, comp_config in config.items():
        if cmptlen == 0 or (cmptlen > 0 and foundcmp(compt, components)):
            receiver = getattr(receivers, comp_config["Receiver"]["class"])
            del comp_config["Receiver"]["class"]
            print("Starting {} ....".format(compt))
            p = Process(target=f, args=(receiver, comp_config))
            p.start()
            p.join()
            time.sleep(1)


@start.command()
@click.option("--config", "-c", default=None, help="Use a custom config file")
@click.argument("components", nargs=-1)
@click.pass_context
def daq(ctx, config, components):
    """ Start receivers daemons\n
            example:\n
                `control-ssdaq start daq Moni Read`\n
            which starts a MonitorReceiver and a ReadoutAssembler
    """
    config = load_config(ctx, config)
    daq_start(config, list(components))


@click.group()
@click.pass_context
def stop(ctx):
    """Stop a running receiver or writer daemon"""
    pass


def daq_stop(config, components):
    cmptlen = len(components)
    for compt, comp_config in config.items():
        if cmptlen == 0 or (cmptlen > 0 and foundcmp(compt, components)):
            receiver = getattr(receivers, comp_config["Receiver"]["class"])
            del comp_config["Receiver"]["class"]
            print("Stopping {} ....".format(compt))
            receiver = RecieverDaemonWrapper(
                receiver, **comp_config["Daemon"], **comp_config
            )
            receiver.stop()


@stop.command()
@click.option("--config", "-c", default=None, help="Use a custom config file")
@click.argument("components", nargs=-1)
@click.pass_context
def daq(ctx, config, components):
    """ Stop receivers daemons\n
            example:\n
                `control-ssdaq stop daq Moni Read`\n
            which stops the MonitorReceiver and ReadoutAssembler
    """
    config = load_config(ctx, config)
    daq_stop(config, list(components))


@click.group()
@click.pass_context
def restart(ctx):  # ,config):
    """Restart receivers or data writers """
    ctx.ensure_object(dict)


@restart.command()
@click.option("--config", "-c", default=None, help="Use a custom config file")
@click.argument("components", nargs=-1)
@click.pass_context
def daq(ctx, config, components):
    """ Restart receivers daemons\n
            example:\n
                `control-ssdaq restart daq Moni Read`\n
            which restarts the MonitorReceiver and ReadoutAssembler
    """
    from copy import deepcopy

    loadedconfig = load_config(ctx, config)
    cmps = list(components)
    daq_stop(deepcopy(loadedconfig), deepcopy(cmps))
    cmps = list(components)
    daq_start(deepcopy(loadedconfig), deepcopy(cmps))


@stop.command()
@click.argument("components", nargs=-1)
@click.pass_context
def dw(ctx, components):
    """Stop a running file writer"""
    import os
    import signal

    components = list(components)
    cmptlen = len(components)
    config = ctx.obj["CONFIG"]
    for compt, comp_config in config.items():
        if cmptlen == 0 or (cmptlen > 0 and foundcmp(compt, components)):
            # for compt in components:
            writer = getattr(subscribers, comp_config["Writer"]["class"])
            del comp_config["Writer"]["class"]
            print("Stopping {}...".format(compt))
            readout_writer = FileWriterDaemonWrapper(
                compt, writer, **comp_config["Daemon"], **comp_config["Writer"]
            )

            try:
                dwpid = readout_writer.getpid()
            except:
                return
            if dwpid != None:
                os.kill(dwpid, signal.SIGHUP)


@click.group(name="roa-ctrl")
@click.pass_context
def roa_ctrl(ctx):
    """Send control commands to a running readout assembler daemon"""
    pass


@roa_ctrl.command()
@click.pass_context
def reset_count(ctx):
    """Resets the readout counter in the readout assembler"""
    import zmq

    zmqctx = zmq.Context()
    sock = zmqctx.socket(zmq.REQ)
    sock.connect("ipc:///tmp/ReadoutAssembler")
    sock.send(b"reset_ro_count 1")
    print(sock.recv())


@roa_ctrl.command()
@click.pass_context
def pause_pub(ctx):
    """Pauses readout publishing"""
    import zmq

    zmqctx = zmq.Context()
    sock = zmqctx.socket(zmq.REQ)
    sock.connect("ipc:///tmp/ReadoutAssembler")
    sock.send(b"set_publish_readouts False")
    print(sock.recv())


@roa_ctrl.command()
@click.pass_context
def restart_pub(ctx):
    """Restart readout publishing"""
    import zmq

    zmqctx = zmq.Context()
    sock = zmqctx.socket(zmq.REQ)
    sock.connect("ipc:///tmp/ReadoutAssembler")
    sock.send(b"set_publish_readouts True")
    print(sock.recv().decode("ascii"))


from multiprocessing import Process
from ssdaq import receivers
import time


def f(receiver, comp_config):
    receiver = RecieverDaemonWrapper(receiver, **comp_config["Daemon"], **comp_config)
    receiver.start(daemon)


def foundcmp(comp, complist):
    for i, c in enumerate(complist):
        if c == comp[: len(c)]:
            del complist[i]
            return True
    else:
        return False


cli.add_command(start)
cli.add_command(stop)
cli.add_command(roa_ctrl)
cli.add_command(restart)


def main():

    cli()


if __name__ == "__main__":
    # control()
    main()
