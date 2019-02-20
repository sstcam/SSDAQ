#!/usr/bin/env python3

import sys
import os
def main():
    from ssdaq import SSReadoutAssembler, ZMQReadoutPublisher
    import time
    import argparse
    from ssdaq.utils import common_args as cargs
    parser = argparse.ArgumentParser(description='Start slow signal data acquisition.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-l', dest='listen_port', type=int,
                        default=2009,
                        help='port for incoming data')

    parser.add_argument('-p', dest='publishing_port', type=int,
                        default=5555,
                        help='port for publishing data')

    parser.add_argument('-i',dest='publishing_interface',type=str,
                        default='127.0.0.101',help='The publishing destination')

    parser.add_argument('-V','--verbosity',nargs='?',const='DEBUG',default='INFO', dest='verbose', type=str,
                        help='Set log level',choices=['DEBUG','INFO','WARN','ERROR','FATAL'])

    parser.add_argument('-r','--relaxed-ip', action='store_true',
                        help='The event builder relaxes the allowed ip range by mapping ip addesses with 2'
                        ' last digits of the address being >32 to valid TM numbers. Note that several'
                        ' ip addresses will map to the same TM. Use this option with cause.')
    cargs.version(parser)
    from ssdaq import sslogger
    import logging;
    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)"%args.verbose)

    ep = ZMQReadoutPublisher(port=args.publishing_port,ip=args.publishing_interface)
    eb = SSReadoutAssembler(relaxed_ip_range=args.relaxed_ip, listen_ip = '0.0.0.0', listen_port = args.listen_port, publishers = [ep])

    eb.run()


if __name__ == "__main__":
    main()