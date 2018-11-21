from ssdaq import SSEventBuilder,ZMQEventPublisher
from ssdaq.utils import daemon


class EventBuilderDaemonWrapper(daemon.Daemon):
    def __init__(self,**kwargs):
        #Deamonizing the server
        daemon.Daemon.__init__(self, '/tmp/ssdaq_daemon.pid',stdout='/tmp/test.log',stderr='/tmp/test.log')
        self.kwargs = kwargs
    def run(self):

            ep = ZMQEventPublisher(**self.kwargs['ZMQEventPublisher'])
            eb = SSEventBuilder(publishers = [ep], **self.kwargs['SSEventBuilder'])
            eb.run()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Start slow signal data acquisition.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('command',  type=str,
                        choices=['start','stop','restart','pause'],
                        help='port for incoming data')

    parser.add_argument('CONFIG', nargs='?', type=str,
                        help='port for publishing data')

    parser.add_argument('-d','--daemonize',action='store_true')
    args = parser.parse_args()
    
    kwargs = {'ZMQEventPublisher':{'port':5555,'ip':'127.0.0.101'},
              'SSEventBuilder':{'relaxed_ip_range':False,'listen_addr':('0.0.0.0',2009)}}
    
    event_builder = EventBuilderDaemonWrapper(**kwargs)
    
    if(args.command=='start'):
        event_builder.start(args.daemonize)
    elif(args.command=='stop'):
        event_builder.stop()



if __name__ == "__main__":
    main()