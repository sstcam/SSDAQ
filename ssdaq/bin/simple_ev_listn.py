import sys
import os
# from os.path import dirname as dn
# sys.path = [dn(dn(dn(os.path.realpath(__file__))))] + sys.path
from ssdaq import SSEventListener
import numpy as np

import argparse

import signal
import sys

def main():

    parser = argparse.ArgumentParser(description='Start a simple event data listener.',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-l', dest='listen_port', type=int,
                        default=5555,
                        help='port for incoming event data')
    parser.add_argument('-i', dest='ip_addr', type=str,
                        default='127.0.0.101',
                        help='The ip/interface which the listener should listen too')
    parser.add_argument('-t',dest='tm_numb',nargs = '?',type=int,help='Set target module number for which SS data is printed out')
    parser.add_argument('-V','--verbosity',nargs='?',const='DEBUG',default='INFO', dest='verbose', type=str,
                        help='Set log level',choices=['DEBUG','INFO','WARN','ERROR','FATAL'])

    parser.add_argument('-n',dest = 'n_events',type=int,default=None,help ='the number of events to listen to before exiting (if not set there is no limit')
    
    args = parser.parse_args()
    from ssdaq import sslogger
    import logging;
    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)"%args.verbose)

    ev_list = SSEventListener(port = args.listen_port, ip = args.ip_addr)
    ev_list.start()

    event_counter = np.zeros(32)
    n_modules_per_event =[]
    n = 0
    signal.alarm(0)
    ctrc_count = 0
    print('Press `ctrl-C` to stop')
    while(True):
        try:
            event = ev_list.get_event()
        except :
            print("\nClosing listener")
            ev_list.close()
            break
        # if(n>0):
        #     print('\033[7   A ')    
        print("Event number %d run number %d"%(event.event_number,event.run_number))
        print("Timestamp %d ns"%(event.event_timestamp))
        print("Timestamp %f s"%(event.event_timestamp*1e-9))
        m = event.timestamps[:,0]>0
        print(np.sum(m))
        print(np.where(m)[0])
        n_modules_per_event.append(np.sum(m))
        print((event.timestamps[m][0,0]*1e-9-event.timestamps[m][:,0]*1e-9))
        event_counter[m] += 1
        m = event_counter>0

        # print(list(zip(np.where(m)[0],event_counter[m])))
        if(args.tm_numb):
            print(event.data[args.tm_numb])
        n +=1
        if(args.n_events != None and n>=args.n_events):
            break
    
    try:
        from matplotlib import pyplot as plt
    except:
        return
    
    plt.figure()
    plt.hist(n_modules_per_event, 10,  facecolor='g', alpha=0.75)
    plt.show()
    ev_list.close()
    ev_list.join()


if __name__ == "__main__":
    main()