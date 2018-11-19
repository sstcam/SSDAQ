#!/usr/bin/env python3

import sys
import os
def main():
    # from os.path import dirname as dn

    # sys.path = [dn(dn(dn(os.path.realpath(__file__))))] + sys.path
    from ssdaq import SSDataListener,SSEventBuilder, SSEventDataPublisher

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

    parser.add_argument('-V','--verbose',nargs='?',const='DEBUG',default='INFO', dest='verbose', type=str,
                        help='Set log level',choices=['DEBUG','INFO','WARN','ERROR','FATAL'])

    parser.add_argument('-r','--relaxed-ip', action='store_true',
                        help='The event builder relaxes the allowed ip range by mapping ip addesses with 2'
                        ' last digits of the address being >32 to valid TM numbers. Note that several'
                        ' ip addresses will map to the same TM. Use this option with cause.')

    from ssdaq import sslogger
    import logging;
    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)"%args.verbose)

    eb = SSEventBuilder(args.verbose,args.relaxed_ip)
    dl = SSDataListener(args.listen_port,eb.data_queue)
    ep = SSEventDataPublisher(args.publishing_port,eb.event_queue)

    dl.start()
    time.sleep(1)
    eb.start()
    time.sleep(1)
    ep.start()


if __name__ == "__main__":
    main()