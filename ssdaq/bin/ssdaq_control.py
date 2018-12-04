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
        eval("sslogger.setLevel(logging.%s)"%log_level)
    def run(self):
            from subprocess import call
            import os
            from ssdaq import sslogger
            

            if(self.set_taskset):
                #forces the process to one particular CPU core
                call(["taskset","-cp", self.core_id,"%s"%(str(os.getpid()))])
            ep = ZMQEventPublisher(**self.kwargs['ZMQEventPublisher'])
            eb = SSEventBuilder(publishers = [ep], **self.kwargs['SSEventBuilder'])
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


def main():
    import argparse
    import yaml
    from pkg_resources import resource_stream,resource_string, resource_listdir
    parser = argparse.ArgumentParser(description='Start slow signal data acquisition.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('command',  type=str,
                        choices=['starteb','startew','stop','restart','pause','reset_event_counter'],
                        help='port for incoming data')

    parser.add_argument('CONFIG', nargs='?', type=str,
                        help='port for publishing data')

    parser.add_argument('-d','--daemonize',action='store_true')
    args = parser.parse_args()
    
    config = yaml.load(resource_stream('ssdaq.resources','ssdaq-default-config.yaml'))
    if(args.CONFIG):
        config = yaml.load(open(args.CONFIG,'r'))
        
    event_builder = EventBuilderDaemonWrapper(**config['EventBuilderDaemon'], **config["EventBuilder"])
    event_writer = EventFileWriterDaemonWrapper(**config['EventFileWriterDaemon'],**config["EventFileWriter"])
    

    if(args.command=='starteb'):
        print('Starting event builder...')
        event_builder.start(args.daemonize)
    elif(args.command=='startew'):
        print('Starting event writer...')
        event_writer.start(args.daemonize)
    elif(args.command=='stop'):
        import os
        import signal
        event_builder.stop()
        try:
            ewpid = event_writer.getpid()
        except:
            return
        if(ewpid != None):
           os.kill(ewpid,signal.SIGHUP)
           import time
           time.sleep(2)
           event_writer.stop()

    elif(args.command=='reset_event_counter'):
        import zmq
        ctx = zmq.Context()  
        sock = ctx.socket(zmq.REQ)  
        sock.connect('ipc:///tmp/ssdaq-control')    
        sock.send(b'reset_ev_count 1')
        print(sock.recv())

if __name__ == "__main__":
    main()