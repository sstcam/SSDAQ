# from ssdaq.core import SSEventBuilder 
from ssdaq.core import SSEventListener

import zmq
import numpy as np
from matplotlib import pyplot as plt


import argparse

parser = argparse.ArgumentParser(description='Start a simple event data listener.',formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-l', dest='listen_port', type=str,
                    default='5555',
                    help='port for incoming event data')

args = parser.parse_args()


ev_list = SSEventListener.SSEventListener(args.listen_port)
ev_list.start()

event_counter = np.zeros(32)
n_modules_per_event =[]
n = 0
while(True):

	event = ev_list.event_buffer.get()
	
	print("Event number %d run number %d"%(event.event_number,event.run_number))
	m = event.timestamps[:,0]>0
	# print(event.timestamps[m])
	print(np.sum(m))
	print(np.where(m)[0])
	n_modules_per_event.append(np.sum(m))
	print((event.timestamps[m][0]-event.timestamps[m])*1e-7)
	event_counter[m] += 1
	m = event_counter>0
	print(list(zip(np.where(m)[0],event_counter[m])))
	if(n>2000):
		break
	n +=1
plt.figure()
plt.hist(n_modules_per_event, 10,  facecolor='g', alpha=0.75)
plt.show()