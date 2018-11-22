from ssdaq import SSEventBuilder,ZMQEventPublisher
from ssdaq.utils import daemon


class EventBuilderDaemonWrapper(daemon.Daemon):
    def __init__(self,**kwargs):
        #Deamonizing the server
        daemon.Daemon.__init__(self, '/tmp/ssdaq_daemon.pid',stdout='/tmp/ssdaq.log',stderr='/tmp/ssdaq.log')
        self.kwargs = kwargs
    def run(self):

            ep = ZMQEventPublisher(**self.kwargs['ZMQEventPublisher'])
            eb = SSEventBuilder(publishers = [ep], **self.kwargs['SSEventBuilder'])
            eb.run()

class EventFileWriterDaemonWrapper(daemon.Daemon):
    def __init__(self,**kwargs):
        #Deamonizing the server
        daemon.Daemon.__init__(self, '/tmp/ssdaq_writer_daemon.pid',stdout='/tmp/ssdaq_writer.log',stderr='/tmp/ssdaq_writer.log')
        self.kwargs = kwargs
    def run(self):
        from ssdaq.event_receivers import EventFileWriter
        import signal
        import sys
        
        
        data_writer = EventFileWriter(**self.kwargs)
        def signal_handler_fact(data_writer):

            def signal_handler(sig, frame):
                data_writer.running = False
                data_writer.event_listener.CloseThread()
                data_writer.join()
            return signal_handler
        signal.signal(signal.SIGHUP, signal_handler_fact(data_writer))

        data_writer.start()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Start slow signal data acquisition.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('command',  type=str,
                        choices=['starteb','startew','stop','restart','pause','reset_event_counter'],
                        help='port for incoming data')

    parser.add_argument('CONFIG', nargs='?', type=str,
                        help='port for publishing data')

    parser.add_argument('-d','--daemonize',action='store_true')
    args = parser.parse_args()
    
    kwargs = {'ZMQEventPublisher':{'port':5555,'ip':'127.0.0.101'},
              'SSEventBuilder':{'relaxed_ip_range':False,'listen_addr':('0.0.0.0',2009)}}
    
    event_builder = EventBuilderDaemonWrapper(**kwargs)
    event_writer = EventFileWriterDaemonWrapper(**{'file_prefix':'/home/sflis/testing_still','file_enumerator':'date'})
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