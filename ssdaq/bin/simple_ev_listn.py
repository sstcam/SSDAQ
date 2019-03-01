from ssdaq import SSReadoutListener
from ssdaq.utils import common_args as cargs
from ssdaq import sslogger
import logging
import numpy as np

import argparse

import signal
from datetime import datetime
def main():

    parser = argparse.ArgumentParser(description='Start a simple Slow Signal readout listener.',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-l', dest='listen_port', type=int,
                        default=5555,
                        help='port for incoming readout data')
    parser.add_argument('-i', dest='ip_addr', type=str,
                        default='127.0.0.101',
                        help='The ip/interface which the listener should listen too')
    parser.add_argument('-t',dest='tm_numb',nargs = '?',type=int,help='Set target module number for which SS data is printed out')
    parser.add_argument('-V','--verbosity',nargs='?',const='DEBUG',default='INFO', dest='verbose', type=str,
                        help='Set log level',choices=['DEBUG','INFO','WARN','ERROR','FATAL'])

    parser.add_argument('-n',dest = 'n_readouts',type=int,default=None,help ='the number of readouts to listen to before exiting (if not set there is no limit')
    cargs.version(parser)

    args = parser.parse_args()
    eval("sslogger.setLevel(logging.%s)"%args.verbose)

    ev_list = SSReadoutListener(port = args.listen_port, ip = args.ip_addr)
    ev_list.start()

    readout_counter = np.zeros(32)
    n_modules_per_readout =[]
    n = 0
    signal.alarm(0)
    print('Press `ctrl-C` to stop')
    while(True):
        try:
            readout = ev_list.get_readout()
        except KeyboardInterrupt:
            print("\nClosing listener")
            ev_list.close()
            break
        # if(n>0):
        #     print('\033[7   A ')
        print("Readout number %d"%(readout.iro))
        print("Timestamp %d ns"%(readout.time))
        print("Timestamp %f s"%(readout.time*1e-9))
        print("Cpu timestamp {}".format(datetime.utcfromtimestamp(readout.cpu_t)))
        print("Cpu timestamp {}".format(readout.cpu_t))
        # print(np.where(m)[0])
        # n_modules_per_readout.append(np.sum(m))
        # readout_counter[m] += 1
        # m = readout_counter>0

        if(args.tm_numb):
            print(readout.data[args.tm_numb])
        n +=1
        if(args.n_readouts != None and n>=args.n_readouts):
            break

    try:
        from matplotlib import pyplot as plt
    except ImportError:
        return

    plt.figure()
    plt.hist(n_modules_per_readout, 10,  facecolor='g', alpha=0.75)
    plt.show()
    ev_list.close()
    ev_list.join()


if __name__ == "__main__":
    main()