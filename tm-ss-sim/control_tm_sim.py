import zmq
import argparse
from subprocess import call
import os
import pickle
parser = argparse.ArgumentParser(description='A simple interface to docker to build and run a TM slow signal simulation\n' 
                                            'with docker containers.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-c','--cmd',nargs='+',help='send command') 

parser.add_argument('-l','--local', action='store_true',
                    help='If the simulation runs on local host use this option.')

parser.add_argument('-p','--port', type = int,default=30001 ,dest= 'port', 
                        help='TM communications port')

parser.add_argument('-i','--ip', type = str,default='172.18.0.102' ,dest= 'ip', 
                        help='TM ip')

args = parser.parse_args()

ctx = zmq.Context()    
com_sock = ctx.socket(zmq.REQ)
if(args.local):
    com_sock.connect('tcp://localhost:30001')
else:
    com_sock.connect('tcp://%s:%d'%(args.ip,args.port))
if(not args.cmd ==None):
    print(' '.join(args.cmd))
    com_sock.send((' '.join(args.cmd)).encode('ascii'))
    reply = pickle.loads(com_sock.recv())
    print('Received reply from: %s@%s'%(reply['name'],reply['ip']))
    print('Status: %s'%reply['status'])
    print(reply['msg'])    
    
    

