import zmq
import argparse
from subprocess import call
import os

parser = argparse.ArgumentParser(description='A simple interface to docker to build and run a TM slow signal simulation\n' 
                                            'with docker containers.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-c','--cmd',nargs='+',help='send command') 

parser.add_argument('-b', dest='build', action='store_true',
                    help='build docker image')


args = parser.parse_args()

ctx = zmq.Context()    
com_sock = ctx.socket(zmq.REQ)
com_sock.connect('tcp://localhost:2001')
if(not args.cmd ==None):
    print(' '.join(args.cmd))
    com_sock.send(' '.join(args.cmd))
    print(com_sock.recv())
    

