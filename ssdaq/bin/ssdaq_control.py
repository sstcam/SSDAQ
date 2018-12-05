from ssdaq import SSEventBuilder,ZMQEventPublisher
from ssdaq.utils import daemon


class EventBuilderDaemonWrapper(daemon.Daemon):
    def __init__(self,stdout = '/dev/null', stderr = '/dev/null', set_taskset = False, core_id = 0,log_level='INFO',**kwargs):
        #Deamonizing the server
        daemon.Daemon.__init__(self, '/tmp/ssdaq_daemon.pid', stdout=stdout, stderr=stderr)
        self.kwargs = kwargs
        self.set_taskset = set_taskset
        self.core_id = str(core_id)
        import logging;
        from ssdaq import sslogger
        eval("sslogger.setLevel(logging.%s)"%log_level)
    def run(self):
            from subprocess import call
            import os
            
            if(self.set_taskset):
                #forces the process to one particular CPU core
                call(["taskset","-cp", self.core_id,"%s"%(str(os.getpid()))])
            eps = []
            i = 1
            for eptype,epconf in self.kwargs['EventPublishers'].items():
                if('name' not in epconf):
                    epconf['name'] = eptype#'ZMQEventPublisher%d'%i
                eps.append(ZMQEventPublisher(**epconf))
                i+=1           
            eb = SSEventBuilder(publishers = eps, **self.kwargs['SSEventBuilder'])
            eb.run()

class EventFileWriterDaemonWrapper(daemon.Daemon):
    def __init__(self,stdout = '/dev/null', stderr = '/dev/null', **kwargs):
        #Deamonizing the server
        daemon.Daemon.__init__(self, '/tmp/ssdaq_writer_daemon.pid', stdout=stdout, stderr=stderr)
        self.kwargs = kwargs
    def run(self):
        from ssdaq.event_receivers import EventFileWriter
        import signal
        import sys

        data_writer = EventFileWriter(**self.kwargs)
        def signal_handler_fact(data_writer):

            def signal_handler(sig, frame):
                data_writer.close()
            return signal_handler
        signal.signal(signal.SIGHUP, signal_handler_fact(data_writer))

        data_writer.start()

import yaml
import click
class MyGroup(click.Group):
    def parse_args(self, ctx, args):
        if args[0] in self.commands:
            if len(args) == 1 or args[1] not in self.commands:
                args.insert(0, '')
        super(MyGroup, self).parse_args(ctx, args)

@click.group()
@click.pass_context
def cli(ctx):
    '''Start, stop and control ssdaq event builder and writer daemons'''
    ctx.ensure_object(dict)
    from pkg_resources import resource_stream,resource_string, resource_listdir
    ctx.obj['CONFIG'] =yaml.load(resource_stream('ssdaq.resources','ssdaq-default-config.yaml')) 
    pass

@click.group(cls=MyGroup)
@click.option('--daemon/--no-daemon','-d',default=False,help='run as daemon')
@click.argument('config',required=False)
@click.pass_context
def start(ctx,daemon,config):#,config):
    '''Start an event builder or writer with and optiononal custom CONFIG file'''
    ctx.ensure_object(dict)
    ctx.obj['DAEMON'] = daemon
    if(config):
        ctx.obj['CONFIG'] = yaml.load(open(config,'r'))
    

@start.command()
@click.pass_context
def eb(ctx):
    '''Start an event builder'''
    print('Starting event builder...')
    config = ctx.obj['CONFIG']
    event_builder = EventBuilderDaemonWrapper(**config['EventBuilderDaemon'], **config["EventBuilder"])
    event_builder.start(ctx.obj['DAEMON'])

@start.command()
@click.pass_context
def ew(ctx):
    '''Start an event writer'''
    print('Starting event writer...')
    config = ctx.obj['CONFIG']
    
    event_writer = EventFileWriterDaemonWrapper(**config['EventFileWriterDaemon'],**config["EventFileWriter"])
    event_writer.start(ctx.obj['DAEMON'])


@click.group(cls=MyGroup)
@click.pass_context
def stop(ctx):
    '''Stop a running eventbuilder or writer'''
    pass


@stop.command()
@click.pass_context
def eb(ctx):
    '''Stop a running event builder'''
    config = ctx.obj['CONFIG']
    event_builder = EventBuilderDaemonWrapper(**config['EventBuilderDaemon'], **config["EventBuilder"])
    event_builder.stop()

@stop.command()
@click.pass_context
def ew(ctx):
    '''Stop a running event writer'''
    config = ctx.obj['CONFIG']
    event_writer = EventFileWriterDaemonWrapper(**config['EventFileWriterDaemon'],**config["EventFileWriter"])
    import os
    import signal
    try:
        ewpid = event_writer.getpid()
    except:
        return
    if(ewpid != None):
       os.kill(ewpid,signal.SIGHUP)
       import time
       time.sleep(2)
       event_writer.stop()

@stop.command()
@click.pass_context
def all(ctx):
    '''Stop both the event builder and writer'''
    eb(ctx)
    ew(ctx)

@click.group(name='eb-ctrl', cls=MyGroup)
@click.pass_context
def eb_ctrl(ctx):
    '''Send control commands to a running event builder daemon'''
    pass

@eb_ctrl.command()
@click.pass_context
def reset_count(ctx):
    '''Resets the event counter in the event builder'''
    import zmq
    zmqctx = zmq.Context()  
    sock = zmqctx.socket(zmq.REQ)  
    sock.connect('ipc:///tmp/ssdaq-control')    
    sock.send(b'reset_ev_count 1')
    print(sock.recv())


cli.add_command(start)
cli.add_command(stop)
cli.add_command(eb_ctrl)

def main():
    
    cli()

if __name__ == "__main__":
    # control()
    main()
