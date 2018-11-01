import zmq
import argparse
from subprocess import call
import os
import pickle
from parse_utils import parse_args

parser = argparse.ArgumentParser(description='Communicate with TM simulation processes to change the simulation dynamically',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter
                                )
parser.add_argument('-V','--verbose', action='store_true', help='Turns on verbosity')


commands = parser.add_subparsers(title='sub-commands')
cmd_parser = commands.add_parser('cmd',formatter_class=argparse.ArgumentDefaultsHelpFormatter, 
                                 help='Send command to a TM simulation process')

cmd_parser.add_argument('cmd',nargs='+',help='Send command CMD [ARG ...] ') 

cmd_parser.add_argument('-l','--local', action='store_true',
                    help='If the simulation runs on local host use this option.')

cmd_parser.add_argument('-p','--port', type = int,default=30001 ,dest= 'port', 
                        help='TM communications port')

cmd_parser.add_argument('-i','--ip', type = str,default='172.18.0.102' ,dest= 'ip', 
                        help='TM ip')

status_parser = commands.add_parser('status',help='Print state of the simulation')


args = parse_args(parser, commands)

ctx = zmq.Context()    

path = os.path.dirname(os.path.abspath(__file__))
#Changing working directory to script location.
os.chdir(path)

if(not args.cmd ==None):
    com_sock = ctx.socket(zmq.REQ)
    if(args.cmd.local):
       com_sock.connect('tcp://localhost:30001')
    else:
       com_sock.connect('tcp://%s:%d'%(args.cmd.ip,args.cmd.port))
    
    print(' '.join(args.cmd.cmd))
    com_sock.send((' '.join(args.cmd.cmd)).encode('ascii'))
    reply = pickle.loads(com_sock.recv())
    print('Received reply from: %s@%s'%(reply['name'],reply['ip']))
    print('Status: %s'%reply['status'])
    print(reply['msg'])

def pretty_cam_print(data_dict,size=4,type='s'):
    size+=1
    ms = ''
    for i in range(6):
        ms += '|%%-%d%s|'%(size,type)
    tbs = ' '*(size+2)
    for i in range(4):
        tbs += '|%%-%d%s|'%(size,type)
    tbs += ' '*size
    print(tbs%(tuple([data_dict[i].center(size,' ') for i in range(0,4)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(4,10)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(10,16)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(16,22)])))
    print(ms%(tuple([data_dict[i].center(size,' ') for i in range(22,28)])))
    print(tbs%(tuple([data_dict[i].center(size,' ') for i in range(28,32)])))

if(not args.status == None):
    tms_running = open('started_tms.txt','r').readlines()
    connections = {}
    tm_dict = {}
    for i in range(32):
        tm_dict[i] = 'TM-%02d OFF'%(i+1)

    for tm in tms_running:
        tm = tm.split()
        connections[tm[0]] = ctx.socket(zmq.REQ)  
        connections[tm[0]].connect('tcp://%s'%(tm[1]))    
        connections[tm[0]].send(b'ping')
        reply = pickle.loads(connections[tm[0]].recv())
        if(args.verbose):
            print(reply)
        if(reply['status'] == 'OK'):
            tm_dict[int(tm[0][2:])] ='TM-%02d ON'%(int(tm[0][2:])+1)

    pretty_cam_print(tm_dict,size=9)    
