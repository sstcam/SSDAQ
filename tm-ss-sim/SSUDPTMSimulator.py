import socket
import os
import numpy as np
import time
from datetime import datetime

import struct
import asyncio
import zmq
import zmq.asyncio
from queue import Queue
import inspect

class TMSimulator(object):
 
    def __init__(self, send_port,server_port, host_ip = None):
        self.corrs = [self.handle_commands(),self.send_ss_data()]
        self.loop = asyncio.get_event_loop()
        self.futures = []


        self.send_port = send_port
        if(host_ip == None):
            self.host_ip = '127.0.0.1'#socket.gethostname()
        else:    
            self.host_ip = host_ip 
        
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host_address = (self.host_ip, send_port)
        self.npackets = 0
        self.nreading = 0
        self.npackets_c = 0
        self.data = np.random.uniform(0,400,64)
        self.sending_ss_data = True
        self.dt = 1.0
        self.t_past = datetime.utcnow()        
        self.t1 = datetime.utcnow()

        self.server_port = server_port
        self.context = zmq.asyncio.Context()    
        self.com_sock = self.context.socket(zmq.REP)
        self.com_sock.bind("tcp://%s:%s"%(self.host_ip,self.server_port))

        method_list = inspect.getmembers(self, predicate=inspect.ismethod)
        self.cmds = {}
        for method in method_list:
            if(method[0][:4] == 'cmd_'):
                self.cmds[method[0][4:]] = method[1]


    def simulate_data(self):
        #simulate next step
        self.data += np.random.uniform(-4,4,64)
        self.data[self.data<0] = 0
        
        #convert mV to counts and correct bit format
        data_counts = np.asarray(self.data/(0.03815*2.),dtype=np.uint16)
        m = data_counts<0x8000
        data_counts[m] +=0x8000
        data_counts[~m]= data_counts[~m]&0x7FFF
        return data_counts.copy()
    
    def cmd_ping(self,arg):
        return 'OK'
    
    def cmd_send_ss_data(self, arg):
        print(arg)
        if(len(arg)==1):
            arg = arg[0]
        else:
            return 'Error'
        if(arg == 'True' or arg == 'true'):
            self.send_ss_data = True
        elif(arg == 'False' or arg == 'false'):
            self.send_ss_data = False
        else:
            return "Error"
        return "OK"

    def cmd_change_rate(self,arg):
        if(len(arg)==1):
            self.dt = 1/float(arg[0])
        else:
            return 'Error'

    def run(self):
        for c in self.corrs:
            self.futures.append(self.loop.create_task(c))
        try:
            self.loop.run_forever()
        except:
            pass
        self.loop.close()

    

    async def handle_commands(self):
        while(True):
            cmd = await self.com_sock.recv()
            print('Handling incoming command %s'%cmd)
            cmd = cmd.decode('ascii').split(' ')
            print(self.cmds.keys())
            print(cmd[0])
            if(cmd[0] in self.cmds.keys()):
                reply = self.cmds[cmd[0]](cmd[1:])
            else:
                reply = "Error"
            await self.com_sock.send(reply.encode())


    async def send_ss_data(self):
        
        while(True):
            timestamp = self.t1.timestamp() + np.random.uniform(-2e-4,2e-4)
            data_packet = bytearray()
            for i in range(10):
                data = self.simulate_data()
                data_packet.extend(struct.pack('>Q',int((timestamp+0.1*self.dt*i)*1e9)))
                data_packet.extend(struct.pack('>32H',*data[:32]))
                data_packet.extend(struct.pack('>Q',int((timestamp+0.1*self.dt*i)*1e9)))
                data_packet.extend(struct.pack('>32H',*data[32:]))
                self.nreading += 1

            sent = self.udp_sock.sendto(data_packet, self.host_address)
            self.npackets_c +=1
            if(self.npackets%10==0):
                t_now = datetime.utcnow()
                dtt = t_now-self.t_past
                self.t_past = t_now

                print("Sent %d packets"%(self.npackets))
                print("Rate %g Hz"%(self.npackets_c/float(dtt.seconds+dtt.microseconds/1000000.0)))
                # print(len(data_packet))
                self.npackets_c =0
            self.npackets +=1

            t2 = datetime.utcnow()
            sleeptime = -(t2-self.t1).microseconds/1000000.0 + self.dt   
            if(sleeptime<0):
                sleeptime = 0
            await asyncio.sleep(sleeptime)
            self.t1 = datetime.utcnow()

        t = datetime.utcnow()


if (__name__ == "__main__"):
    
    # import argparse
    # import os

    # parser = argparse.ArgumentParser(description='A simple interface to docker to build and run a TM slow signal simulation\n' 
    #                                             'with docker containers.',
    #                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # parser.add_argument('-c','--cmd',nargs='+',help='send command') 

    # parser.add_argument('-b', dest='build', action='store_true',
    #                     help='build docker image')


    # args = parser.parse_args()
    
    import sys
    # port = int(sys.argv[1])
    # host_ip = sys.argv[2]#"172.17.0.1"
    send_port = 2009
    server_port = 2001
    tmsim = TMSimulator(send_port,server_port)
    tmsim.run()

