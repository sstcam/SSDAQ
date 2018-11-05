from ssdaq.event_receivers import EventFileWriter

import argparse


parser = argparse.ArgumentParser(description='Start a simple event data writer.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-l', dest='listen_port', type=str,
                    default='5555',
                    help='port for incoming event data')

parser.add_argument('filename', type=str,
                    default='5555',
                    help='Output file name')

args = parser.parse_args()


data_writer = EventFileWriter.EventFileWriter(args.filename)

data_writer.start()

running = True
while(running):
    ans = input('To stop type `yes`:')
    if(ans == 'yes'):
        data_writer.running = False
        running = False
data_writer.join()

