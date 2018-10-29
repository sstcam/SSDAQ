import argparse
from subprocess import call
import os

parser = argparse.ArgumentParser(description='A simple interface to docker to build and run a TM slow signal simulation\n' 
                                            'with docker containers.',
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-b', dest='build', action='store_true',
                    help='build docker image')


parser.add_argument('-p', dest='print_args', action='store_true',
                    help='print input arguments')

parser.add_argument('-n', '--network-name',dest='network_name', type=str,
                    default='my-net',
                    help='docker network/bridge name')

parser.add_argument('-i', '--ip', type=str,
                    default='172.18.0.',
                    help='network ip for the tm modules')


parser.add_argument('-N', '--number of modules',dest='n_modules', type=str,
                    default='32',
                    help='Number of tm modules to simulate')
    
parser.add_argument('-r', '--run', action='store_true',
                    help='run simulation')

parser.add_argument('-s', '--stop', action='store_true',
                    help='Stop running containers with TM simulation')

args = parser.parse_args()

path = os.path.dirname(os.path.abspath(__file__))


if(args.print_args):
    for key,value in vars(args).iteritems():
        print(key,value)

if(args.build):
    call_list =["/usr/bin/docker", "build", "-t", "ss-sim", '.'] 
    call(call_list)

if(args.run):
    started_modules = []
    for i in range(int(args.n_modules)):
        sim_name = 'TM%d'%i
        started_modules.append(sim_name)
        cmd_list = ["docker", 
            "run",
            '--name', '%s'%(sim_name),
            '--net', '%s'%(args.network_name),
            '--ip','%s1%02d'%(args.ip,i+1),
            '-d',
            '--rm',   
            'ss-sim']
        print(' '.join(cmd_list))
        call(cmd_list)
        f = open('started_tms.txt','w')
        f.writelines([n+'\n' for n in started_modules])
    print('Started %d container(s)'%(i+1))

if(args.stop):
    if(os.path.isfile('started_tms.txt')):
        tms_to_stop = open('started_tms.txt','r').readlines()
        for tm in tms_to_stop:
            cmd_list = ['docker','rm','-f',tm[:-1]]
            print(cmd_list)
            call(cmd_list)
        os.remove('started_tms.txt')
        print('Removed %d container(s)'%len(tms_to_stop))
    else:
        print('No container file found')
        print('Not stopping any simulations')
# build_coomand = 



