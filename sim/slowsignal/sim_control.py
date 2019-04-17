import zmq
import argparse
from subprocess import call
import os
import pickle
from sim_utils import *


class SimControl(object):
    def __init__(self, subprogram_list):

        self.parser = argparse.ArgumentParser(
            description="Communicate with TM simulation processes to change the simulation dynamically",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self.parser.add_argument(
            "-V", "--verbose", action="store_true", help="Turns on verbosity"
        )
        self.commands = self.parser.add_subparsers(title="Commands")

        self.subprograms = {}
        for sp in subprogram_list:
            self.subprograms[sp.init_parser(self.commands)] = sp

    def run(self):
        args = parse_args(self.parser, self.commands)
        if args.verbose:
            print(args)

        for k, v in vars(args).items():
            if v != None and k in self.subprograms:
                self.subprograms[k].run(v, args)


class StatusQuery(object):
    def __init__(self, name="status"):
        self.name = name
        self.queries_map = {
            "npackets": b"get_npackets_sent",
            "ss-rate": b"get_rate",
            "sending": b"is_sending_ss_data",
        }

    def init_parser(self, cmd_parser):
        self.status_parser = cmd_parser.add_parser(
            "status",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            help="Print state of the simulation",
            description="Some description",
        )
        self.status_parser.add_argument(
            "query",
            nargs="?",
            choices=list(self.queries_map.keys()),
            help="Status or setting to query. If no query is given, running modules are shown",
        )
        self.status_parser.add_argument(
            "-n",
            "--n-updates",
            type=int,
            default=1,
            help="Number of subsequent updates",
        )
        self.status_parser.add_argument(
            "-u",
            "--update-freq",
            type=float,
            default=1.0,
            help="Time between updates in seconds.",
        )
        self.status_parser.add_argument(
            "-t",
            "--tm-numbering",
            action="store_true",
            help="Turns on TM enumeration when printing status",
        )
        return self.name

    def run(self, args, sup_args):
        import time

        self.sargs = sup_args
        if sup_args.verbose:
            print("Entering status-subprogram")
            print(args)
        self.ctx = zmq.Context()
        self.args = args
        path = os.path.dirname(os.path.abspath(__file__))
        # Changing working directory to script location.
        os.chdir(path)

        if sup_args.verbose:
            print("Changed working directory to %s" % path)
        n_updates = args.n_updates
        if args.query == None:
            while n_updates > 0:
                query = self._query()
                for k, v in query.items():
                    if v == None:
                        query[k] = msg.colr("rf", "OFF")
                    else:
                        query[k] = msg.colr("gf", "ON")

                pretty_cam_print(query, size=8, tm_numbers=args.tm_numbering)
                n_updates -= 1
                if n_updates > 0:
                    time.sleep(args.update_freq)
                    clear_pretty_cam_print(args.tm_numbering)
        else:
            while n_updates > 0:
                query = self._query(self.queries_map[args.query])
                for k, v in query.items():
                    if v == None:
                        query[k] = "--"
                    else:
                        query[k] = tof("{}".format(v))
                n_updates -= 1
                pretty_cam_print(query, size=8, tm_numbers=args.tm_numbering)
                if n_updates > 0:
                    time.sleep(args.update_freq)
                    clear_pretty_cam_print(args.tm_numbering)

    def _query(self, query=b"ping"):
        tm_dict = {}
        for i in range(32):
            tm_dict[i] = None
        tms_running = open(".started_tms.txt", "r").readlines()
        connections = {}
        for tm in tms_running:
            tm = tm.split()
            connections[tm[0]] = self.ctx.socket(zmq.REQ)
            connections[tm[0]].connect("tcp://%s" % (tm[1]))
            connections[tm[0]].send(query)
            reply = pickle.loads(connections[tm[0]].recv())
            if self.sargs.verbose:
                print_message(reply)
            if reply["status"] == "OK":
                tm_dict[int(tm[0][2:])] = reply["msg"]

        return tm_dict


class DirectCommand(object):
    def __init__(self, name="cmd"):
        self.name = name

    def init_parser(self, cmd_parser):
        self.cmd_parser = cmd_parser.add_parser(
            self.name,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            help="Send command to a TM simulation process",
        )

        self.cmd_parser.add_argument(
            "COMMAND", nargs="+", help="Send command CMD [ARG ...] "
        )

        self.cmd_parser.add_argument(
            "-l",
            "--local",
            action="store_true",
            help="If the simulation runs on local host use this option.",
        )

        self.cmd_parser.add_argument(
            "-p",
            "--port",
            type=int,
            default=30001,
            dest="port",
            help="TM communications port",
        )

        self.cmd_parser.add_argument(
            "-i", "--ip", type=str, default="172.18.0.102", dest="ip", help="TM ip"
        )
        return self.name

    def run(self, args, sup_args):
        self.sargs = sup_args
        if sup_args.verbose:
            print("Entering DirectCommand-subprogram")
            print(args)
        self.ctx = zmq.Context()
        self.args = args
        com_sock = self.ctx.socket(zmq.REQ)
        path = os.path.dirname(os.path.abspath(__file__))
        # Changing working directory to script location.
        os.chdir(path)

        if args.local:
            com_sock.connect("tcp://localhost:30001")
        else:
            if "TM" in args.ip:
                if self.sargs.verbose:
                    print("Looking up ip for %s:" % args.ip)
                tms_running = open(".started_tms.txt", "r").readlines()
                ip = None
                for tm in tms_running:
                    if args.ip in tm:
                        ip = tm.split()[1].split(":")[0]
                        break
                if ip == None:
                    raise RuntimeError
                if self.sargs.verbose:
                    print("   %s" % ip)
            else:
                ip = args.ip
            con_str = "tcp://%s:%d" % (ip, args.port)
            if self.sargs.verbose:
                print("Connecting to:\n   %s" % con_str)
            com_sock.connect(con_str)

        com_sock.send((" ".join(args.COMMAND)).encode("ascii"))
        reply = pickle.loads(com_sock.recv())
        print("Received reply from: %s@%s" % (reply["name"], reply["ip"]))
        print("Status: %s" % reply["status"])
        print(reply["msg"])


class DockerCommand(object):
    def __init__(self, name="docker"):
        self.name = name

    def init_parser(self, cmd_parser):
        self.parser = cmd_parser.add_parser(
            self.name,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            help="Interface to build, start and stop docker containers with TM simulators",
        )
        self.parser.add_argument(
            "docker-command",
            nargs="+",
            help="Docker command",
            choices=["run", "build", "stop"],
        )

        self.parser.add_argument(
            "-n",
            "--network-name",
            dest="network_name",
            type=str,
            default="my-net",
            help="docker network/bridge name",
        )

        self.parser.add_argument(
            "-i",
            "--ip",
            type=str,
            default="172.18.0.",
            help="network ip for the tm modules",
        )
        return self.name

    def run(self, args, sup_args):
        self.sargs = sup_args
        self.args = args
        print("DockerCommand")
        print(args)
        path = os.path.dirname(os.path.abspath(__file__))
        # Changing working directory to script location.
        os.chdir(path)

        if os.getuid() > 0:
            print("Need to be root to execute docker commands")
            exit()

        if self.args == "build":
            call_list = ["/usr/bin/docker", "build", "-t", "ss-sim", "."]
            call(call_list)

        if self.args == "stop":
            if os.path.isfile(".started_tms.txt"):
                tms_to_stop = open(".started_tms.txt", "r").readlines()
                for tm in tms_to_stop:
                    cmd_list = ["docker", "rm", "-f", tm.split()[0]]
                    print(" ".join(cmd_list))
                    call(cmd_list)
                os.remove(".started_tms.txt")
                print("Removed %d container(s)" % len(tms_to_stop))
            else:
                print("No container file found")
                print("Not stopping any simulations")


subprg_list = [StatusQuery(), DirectCommand(), DockerCommand()]
sim_ctrl = SimControl(subprg_list)
sim_ctrl.run()
