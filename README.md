# SSDAQ
[![Build Status](https://travis-ci.org/cta-chec/SSDAQ.svg?branch=master)](https://travis-ci.org/cta-chec/SSDAQ) [![Coverage Status](https://coveralls.io/repos/github/sflis/SSDAQ/badge.svg?branch=master)](https://coveralls.io/github/sflis/SSDAQ?branch=master)

Data acquisition and distribution for CHEC-S TARGET-C modules.

This project contains a set of modules and applications to receive and handle pushed data from the CHEC camera. The data is then published on TCP sockets that are subscribable. Subscribers for printing out the data or writing it to disk are provided as well. 


## Installation
For a normal install run

`python setup.py install`

or in the root directory of the project do

`pip install .`

If you are developing it is recommendended to do

`pip install -e .`

instead and adding the `--user` option if not installing in a conda env. This lets changes made to the project automatically propagate to the install without the need to reinstall.


## Usage

The SSDAQ software package contains applications for CHEC-S pushed data acqusition and writing that data to disk, but can also be use as a python library to write custom subscribers, and to read and write slow signal, trigger, timestamp, log or monitoring data.

### Applications
A range of applications are provided in the SSDAQ software package and if the install is sucessful these should all be in your path. The majority of the applications are different types of subscribers and the executables are prefixed with `chec-<name>-<type>`, where `<type>` is the type of subscriber which will be explained shortly and `<name>` refers to the data which it subscribes to. Currently there are three types of subscribers, `chec-dumpers` which dump the content they receive directly in the terminal std output, `chec-writer` are as the name suggests subscribers that write to file and lastly we have the `chec-daq-dash`, a simple terminal dash showing monitoring data from the receivers.   

Starting and stopping the receivers should be done with the `control-ssdaq` application which starts the receivers as deamons and configures the logging so that it is output on a dedicated port. More on how to use `control-ssdaq` follows in the next section.

All the applications provide help options explaining the needed input.

#### Using `control-ssdaq`
The `control-ssdaq` application manages the receiver and file writer daemons. The program consists of a number of commands and subcommands and each of the commands and subcommands provides a `--help -h` option and the top help message is shown here:
```shell
Usage: control-ssdaq [OPTIONS] COMMAND [ARGS]...

  Start, stop and control receiver and writer daemons

Options:
  -v, --version  Show version
  -h, --help     Show this message and exit.

Commands:
  roa-ctrl  Send control commands to a running readout assembler daemon
  start     Start receivers or data writers
  stop      Stop a running receiver or writer daemon
```

 The program provides two main commands `start` and `stop` for starting and stopping the daemons. Additionally there is the `roa-ctrl` command to send control commands to the readout assembler. 
 
 ##### Start and stop receiver daemons
 The recommended way of starting the receivers is by using the command
 
 ```control-ssdaq start daq```

which starts all receivers that are configured in the default configuration. To start with a custom configuration one can specify a file with the `--config, -c` option. The `start daq` command also takes arguments that select which receivers to start *e.g*

```control-ssdaq start daq Trigg Read```

 will only start the `TriggerPacketReceiver` and `ReadoutAssembler`. Note that you only have to spell out enough of the receiver class name to make it unique. An empty arg list will start all receivers as seen earlier.

Receivers can be stopped in by using the `stop daq` command in the same manner that we started them, *i.e*

```control-ssdaq stop daq ```
 
 would stop all running receiver daemons while
 
 ```control-ssdaq stop daq Trigg Read```
 
 would only stop the `TriggerPacketReceiver` and `ReadoutAssembler` daemons.
 
##### Start and stop filewriter daemons
Currently only the `ReadoutFileWriter` daemon is supported and it is started with

```control-ssdaq start dw  path/to/configfile.yaml -d ```
and stopped with
```control-ssdaq stop dw ```

Note that if `-d` is ommited the writer will not run as a daemon, which can be good sometimes during testing, and output it's log messages directly in the terminal. To stop it type `ctrl+C`.

##### List of receivers

| Receiver              | Usage              | 
| --------------------- |:------------------:|
| ReadoutAssembler      | Receives slow signal data from the FEE TMs and assembled them into a full camera readout|
| TriggerPacketReceiver | Receives trigger pattern packets from the backplane|
| TimestampReceiver     | Recieves timestamps from the timing board|
| LogReceiver           | Receives logs that are send on port `10001` |
| MonitorReceiver       | Receives monitor data that is pushed on port `10002`|
| TelDataReceiver       | Queries the ASTRI telescope database |
##### List of standard port numbers used

| Port          | Usage              | Which application  |
| ------------- |:------------------:| ------------------:|
| 17000         | listen (UDP)       | ReadoutAssembler|
| 8307          | listen (UDP)       | TriggerPacketReceiver |
| 6666          | subscribe (TCP/ZMQ)| TimestampReceiver  |
| 9001          | publish  (TCP/ZMQ) | LogReceiver  |
| 9002          | publish  (TCP/ZMQ) | TriggerReceiver  |
| 9003          | publish  (TCP/ZMQ) | TimestampReceiver  |
| 9004          | publish  (TCP/ZMQ) | ReadoutAssembler  |
| 9005          | publish  (TCP/ZMQ) | MonitorReceiver  |
| 9006          | publish  (TCP/ZMQ) | TelDataReceiver|
| 10001         | listen  (TCP/ZMQ)  | LogReceiver  |
| 10002         | pull  (TCP/ZMQ)    | MonitorReceiver  |

##### Configuration file for `control-ssdaq`

This is an example configuration showing different aspects of the configuration possibilities.
```yaml
ReadoutAssembler:
  Daemon:
    #redirection of output (should be /dev/null when logging is fully configurable)
    stdout: '/tmp/ssdaq.log'
    stderr: '/tmp/ssdaq.log'
    set_taskset: true #Using task set to force kernel not to swap cores
    core_id: 0 #which cpu core to use with taskset
  Receiver:
    class: ReadoutAssembler
    listen_ip: 0.0.0.0
    listen_port: 17000
    relaxed_ip_range: false
    buffer_length: 1000
    readout_tw: !!float 1.e7 #nano seconds
    buffer_time: !!float 4e9
  Publishers: #Listing publishers
    ZMQReadoutPublisherLocal: #name
      class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
      ip: 127.0.0.101
      port: 9004
    # Dumper: #name
    #   class: RawWriter #class
    #   file_name: 'bindump.dat'
    # ZMQReadoutPublisherOutbound: #name
    #   class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
    #   ip: 141.34.29.161
    #   port: 9999
    #   mode: outbound

LogReceiver:
  Daemon:
    #redirection of output (should be /dev/null when logging is fully configurable)
    stdout: '/tmp/logrec.log'
    stderr: '/tmp/logrec.log'
    set_taskset: true #Using task set to force kernel not to swap cores
    core_id: 0 #which cpu core to use with taskset
  Receiver:
    class: LogReceiver
    ip: 0.0.0.0
    port: 10001
  Publishers: #Listing publishers
    ZMQReadoutPublisherLocal: #name
      class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
      ip: 127.0.0.101
      port: 9001

TriggerReceiver:
  Daemon:
    #redirection of output (should be /dev/null when logging is fully configurable)
    stdout: '/tmp/triggrec.log'
    stderr: '/tmp/triggrec.log'
    set_taskset: true #Using task set to force kernel not to swap cores
    core_id: 0 #which cpu core to use with taskset
  Receiver:
    class: TriggerPacketReceiver
    ip: 0.0.0.0
    port: 8307
  Publishers: #Listing publishers
    ZMQReadoutPublisherLocal: #name
      class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
      ip: 127.0.0.101
      port: 9002

TimestampReceiver:
  Daemon:
    #redirection of output (should be /dev/null when logging is fully configurable)
    stdout: '/tmp/timerec.log'
    stderr: '/tmp/timerec.log'
    set_taskset: true #Using task set to force kernel not to swap cores
    core_id: 0 #which cpu core to use with taskset
  Receiver:
    class: TimestampReceiver
    ip: 192.168.101.102
    port: 6666
  Publishers: #Listing publishers
    ZMQReadoutPublisherLocal: #name
      class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
      ip: 127.0.0.101
      port: 9003


MonitorReceiver:
  Daemon:
    #redirection of output (should be /dev/null when logging is fully configurable)
    stdout: '/tmp/monrec.log'
    stderr: '/tmp/monrec.log'
    set_taskset: true #Using task set to force kernel not to swap cores
    core_id: 0 #which cpu core to use with taskset
  Receiver:
    class: MonitorReceiver
    ip: 0.0.0.0
    port: 10002
  Publishers: #Listing publishers
    ZMQReadoutPublisherLocal: #name
      class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
      ip: 127.0.0.101
      port: 9005

```

###  SSDAQ python library
The `ssdaq` python module provides tools for creating your own listeners or reading and writing slow signal data.

#### Reading and Writing Slow Signal data
The easiest way to read slow signal data is to use the `SSDataReader` class. An example of this is shown below
```python
from ssdaq.data.io import SSDataReader
import numpy as np
reader = SSDataReader('RandomSlowSignal10.hdf5')
print('This file has %d readouts'%reader.n_readouts)
print(reader)
#loop over readouts
for r in reader.read(start=0,stop=10):#the arguments are optional (loops over the whole file if omitted)
	print(reader.iro,np.max(reader.data))

reader.close_file()
```

You can also write data if you want:
```python
from ssdaq.data.io import SSDataWriter
from ssdaq.data import SSReadout
import numpy as np
writer = SSDataWriter('RandomSlowSignal10.hdf5')
for i in range(100):
    ro = SSReadout(timestamp=i*100,
                   readout_number=i,
                   cpu_t_s=i*10,
                   cpu_t_ns=i*10000,
                   data=np.random.random((32,64)),)
    writer.write_readout(ro)
writer.close_file()
```

#### Writing your own receiver
The `SSReadoutListener` class provides an easy way to listen to the data stream generated by `SSReadoutAssembler`. Writing a readout listener can be as simple as:

```python
from ssdaq import SSReadoutListener
ro_list = SSReadoutListener(port = 5555, ip ='127.0.0.1')
ro_list.start() #Starts listener thread
while(True):
    try:
    	# retreive readout from readout buffer (blocking call
	# if block or timeout not specified see queue.Queue docs)
        readout = ro_list.get_readout()
    	#if the readout is of type 'None' the listener thread has been closed.
	if(readout == None):
	    break
    except :
        print("\nClosing listener")
        ro_list.close()
        break
    #do stuff with readout
```

The `try` statement around `readout = ro_list.get_readout()` makes it possible to exit the script gracefully by pressing `ctrl+C`. While handling the exception `close()` is called on the listener which sends a signal to the listener thread to finish and empties the readout buffer. The readout object (`SSReadout`) retreived from the `SSReadoutListener` is defined in `ssdaq/core/ss_data_classes.py`.

### Simulating slow signal data from TMs
A python script that contains a simple simulation of the slow signal output from a TM is provided in this package in the folder `tm-ss-sim`.
To run it locally the following command can be used:

`python3 tm-ss-sim/SSUDPTMSimulator.py 2009 localhost`

which sets the simulation to send the data to port 2009 on localhost. For now the simulation sends ten readouts of random data that slowly fluctuates once per second. However, using this method only one TM can be simulated, but if docker containers are used for each TM then a complete camera can be simulated on a single laptop.

#### Docker instructions to simulate multiple modules sending SS-data from the CHEC camera
To simulate multiple TARGET modules sending slow signal data several docker containers have to be used asigned with a specific IP as the module is identified by the IP in the UDP header of the data packets it sends. Useful docker commands are listed below:

*  build docker image with:
   `docker build -t ss-sim .`
*  setup your own docker network/bridge (Need to check command!)
   `docker network create --driver=bridge --subnet=192.168.0.0/16 br0`
*  run container with TM sim:
  `docker run --net my-net --ip 172.18.0.1xx ss-sim`

the xx should be replaced by a number between 1 and 32 which corresponds to
the module number in the CHEC-camera

These commands might need to be prepended by sudo depending on how docker was installed on the machine. The network only needs to be created once while the `docker build` needs to be run everytime the simulation script to update the image.

To further make the handling of the simulation easier a small script,`docker-command.py` , that interfaces docker is provided. Starting a 32 module simulation is done by

`python tm-ss-sim/docker-command.py -r -N 32`

and can be stopped by

`python tm-ss-sim/docker-command.py -s`

more help is of course given by using the help option (`-h` or `--help`).
