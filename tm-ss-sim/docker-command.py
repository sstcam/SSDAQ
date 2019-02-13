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

path = os.path.dirname(os.path.abspath(__file__))
#Changing working directory to script location.
os.chdir(path)


args = parser.parse_args()
if(os.getuid()>0):
    print("Need to be root to execute docker commands")

    exit()

if(args.print_args):
    for key,value in vars(args).iteritems():
        print(key,value)

if(args.build):
    call_list =["/usr/bin/docker", "build", "-t", "ss-sim", '.']
    call(call_list)

if(args.run):
    started_modules = []
    com_port = 30001
    if(os.path.isfile('.started_tms.txt')):
        print('Alrady started TM simulations')
        print('Stop them first to start more')
        exit()
    for i in range(int(args.n_modules)):
        sim_name = 'TM%d'%i
        ip = '%s1%02d'%(args.ip,i)
        cmd_list = ["docker",
            "run",
            '--name', '%s'%(sim_name),
            '--net', '%s'%(args.network_name),
            '--ip',ip,
            '-d',
            '--rm',
            '-e',
            "MY_IP=%s"%(ip),
            '-e',
            "COM_PORT=%d"%com_port,
            '-e',
            "TM_ID=%d"%i,
            'ss-sim']

        print(' '.join(cmd_list))
        call(cmd_list)
        started_modules.append("%s %s:%s"%(sim_name,ip,com_port))
        # com_port +=1

    f = open('.started_tms.txt','w')
    f.writelines([n+'\n' for n in started_modules])
    print('Started %d container(s)'%(i+1))

if(args.stop):
    if(os.path.isfile('.started_tms.txt')):
        tms_to_stop = open('.started_tms.txt','r').readlines()
        for tm in tms_to_stop:
            cmd_list = ['docker','rm','-f',tm.split()[0]]
            print(' '.join(cmd_list))
            call(cmd_list)
        os.remove('.started_tms.txt')
        print('Removed %d container(s)'%len(tms_to_stop))
    else:
        print('No container file found')
        print('Not stopping any simulations')



