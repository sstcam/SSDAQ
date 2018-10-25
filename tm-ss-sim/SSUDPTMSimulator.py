import socket
import os
import numpy as np
import time
from datetime import datetime

import struct

class TMSimulator(object):
    def __init__(self, port, ip):
        self.port = port
        self.host_ip = ip
        self.data = np.random.uniform(0,400,64)

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

    def Run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        server_address = (self.host_ip, port)
        npackets = 0
        nreading = 0
        
        t = datetime.utcnow()
        while(True):
            timestamp = t.timestamp() + np.random.uniform(-2e-4,2e-4)
            data_packet = bytearray()
            for i in range(10):
                data = self.simulate_data()
                data_packet.extend(struct.pack('>Q',int((timestamp+0.1*i)*1e9)))
                data_packet.extend(struct.pack('>32H',*data[:32]))
                data_packet.extend(struct.pack('>Q',int((timestamp+0.1*i)*1e9)))
                data_packet.extend(struct.pack('>32H',*data[32:]))
                nreading += 1

            sent = sock.sendto(data_packet, server_address)
            if(npackets%10==0):
                print("Sent %d packets"%(npackets))
                print(len(data_packet))
            npackets +=1
            t = datetime.utcnow()
            sleeptime = 1.0 - (t.microsecond/1000000.0)
            time.sleep(sleeptime)

if (__name__ == "__main__"):
    import sys
    port = int(sys.argv[1])
    host_ip = sys.argv[2]#"172.17.0.1"

    tmsim = TMSimulator(port,host_ip)
    tmsim.Run()

