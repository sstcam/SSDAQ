from ssdaq.core.SSDataListener import SSDataListener
from ssdaq.core.SSEventBuilder import SSEventBuilder
from ssdaq.core.SSEventDataPublisher import SSEventDataPublisher

import time
import argparse

parser = argparse.ArgumentParser(description='Start slow signal data acquisition.',
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-l', dest='listen_port', type=str,
                    default='2009',
                    help='port for incoming data')

parser.add_argument('-p', dest='publishing_port', type=str,
                    default='5555',
                    help='port for publishing data')

parser.add_argument('-V','--verbose', dest='verbose', action='store_true',
                    help='Turn on verbose mode')

args = parser.parse_args()

eb = SSEventBuilder(args.verbose)
dl = SSDataListener(args.listen_port,eb.data_queue)
ep = SSEventDataPublisher(args.publishing_port,eb.event_queue)

dl.start()
time.sleep(1)
eb.start()
time.sleep(1)
ep.start()
