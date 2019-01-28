# SSDAQ 
![Test Status Travis-CI](https://travis-ci.org/sflis/SSDAQ.svg?branch=master) [![Coverage Status](https://coveralls.io/repos/github/sflis/SSDAQ/badge.svg?branch=master)](https://coveralls.io/github/sflis/SSDAQ?branch=master)

Slow signal data acquisition and distribution for CHEC-S TARGET-C modules. 

This project contains a set of modules and scripts to receive slow signal data via UDP from TARGET-C modules (TM), build events from data recieved from multiple TMs and publish these  events on a tcp zmq PUB socket. There are also classes and scripts for receiving publishe slow signal readout data and writing them to disk.


## Installation
For a normal install run 

`python setup.py install`

or in the root directory of the project do

`pip install .`

If you are developing it is recommendended to do

`pip install -e .`

instead and adding the `--user` option if not installing in a conda env. This lets changes made to the project automatically propagate to the isntall without the need to reinstall. 

#### Prerequisites

The project is written assuming it will be run with python3.5 or above. Additional dependencies to run the base part of the projects are listed here: 

* python >= 3.5
* numpy
* zmq
* pytables
* pyparsing 
* pyyaml

Some receivers might have additional prerequesites not listed above. These dependencies might include:

* matplotlib
* docker
* urwid
* target_driver
* target_io
* target_calib

## Usage
The SSDAQ software package contains applications for CHEC-S slow signal readout assembling and writing to disk, but can also be use as a python library to  write custom listeners as well as custom readout publishers that can be used by the readout assembler daemon.

### Applications
Currently four applications are provided in the SSDAQ software package which are listed below

* `ssdaq`
* `ssdatawriter`
* `ss-example-listener`
* `control-ssdaq`

The `ssdaq` and `ssdaqwriter` applications directly starts a builder and a writer, respectively. However these applications don't expose all configurable settings of the builder and writer and are provided for quick tests and 1-off runs.

The proper way of starting and controling the slow signal readout assembler is to use `control-ssdaq` together with configuration files, which also can start a file writer. This is explained more in the next section.  
The `ss-example-listener` provides a simple listener which outptus some fields of the published data. 

All the applications provide help options explaining the needed input.
#### Using `control-ssdaq`
The `control-ssdaq` application manages two daemons that can be started seperatley, namely the readout assembler and an data file writer daemon. The program consists of a number of commands and subcommands and each of the commands and subcommands provides a `--help -h` option and the top help message is shown here:
```
Usage: control-ssdaq [OPTIONS] COMMAND [ARGS]...

  Start, stop and control ssdaq readout assembler and writer daemons

Options:
  -h, --help  Show this message and exit.

Commands:
  roa-ctrl  Send control commands to a running readout assembler daemon
  start    Start a readout assembler or writer
  stop     Stop a running readout assembler or writer
```

 The program provides two main commands `start` and `stop` for starting and stopping the daemons. Additionally there is the `roa-ctrl` command to send control commands to the readout assembler. The two daemons for readout assembling and data writing are referred to as `roa` and `dw`, respectively. Therefore, to start an readout assembler as a daemon one could run: 
 
 `control-ssdaq start roa -d`. 
 
In the example above the readout assembler was started with a default configuration provided in the `ssdaq/resources` folder in the porject.  
##### Configuration file for `control-ssdaq`

This is an example configuration showing different aspects of the configuration possibilities. 
```yaml
# Configuration for the file writer class 
SSFileWriter:
  file_enumerator: date #enumerates with timestamp (yr-mo-dy.H.M) or `order` which enumerates with numbers starting from 00001 
  file_prefix: SlowSignalData
  folder: /tmp/
  ip: 127.0.0.101
  port: 5555
# Configuration for the writer daemon wrapper 
ReadoutFileWriterDaemon:
  #redirection of output (should be /dev/null when logging is fully configurable)
  stdout: '/tmp/ssdaq_writer.log'
  stderr: '/tmp/ssdaq_writer.log'

# Configuration for the readout assembler daemon wrapper 
ReadoutAssemblerDaemon:
  #redirection of output (should be /dev/null when logging is fully configurable)
  stdout: '/tmp/ssdaq.log'
  stderr: '/tmp/ssdaq.log'
  set_taskset: true #Using task set to force kernel not to swap cores
  core_id: 0 #which cpu core to use with taskset
# Configuration of the readout assembler
# Note that the readout assembler consists of the SSReadoutAssembler class 
# and some number of publisher instances 
ReadoutAssembler:
  SSReadoutAssembler:
    listen_ip: 0.0.0.0
    listen_port: 2009
    relaxed_ip_range: false
    buffer_length: 1000
    readout_tw: !!float 1.e7 #nano seconds
    buffer_time: !!float 4e9
  ReadoutPublishers:
    #This publisher publishes events  on the local interface at port 5551
    ZMQReadoutPublisherLocal: #Name of the publisher (must be unique)
      ip: 127.0.0.101 
      port: 5551
    #This is an outbound publisher which remote clients can subscribe to
    ZMQReadoutPublisherOutbound:
      ip: 141.34.29.161 #the local, public interface at which events should be published
      port: 9999
      mode: outbound #the mode (by default set to local) determines how the sockets are configured
    #This is a remote publisher that send events to a remote ip and publishes them there
    ZMQReadoutPublisherRemote:
      ip: 141.34.229.11 #the remote ip where the events should be published
      port: 9999
      mode: remote #the mode (by default set to local) determines how the sockets are configured

```
###  SSDAQ python library
The `ssdaq` python module provides tools for creating your own listeners or reading and writing slow signal data. 

#### Reading and Writing Slow Signal data
The easiest way to read slow signal data is to use the `SSDataReader` class. An example of this is shown below  
```python
from ssdaq import SSDataReader
import numpy as np
reader = ssdaq.SSDataReader('path/to/ssdata.hdf5')
print('This file has %d readouts'%reader.n_readouts)
#loop over readouts
for r in reader.read(start=0,stop=10):#the arguments are optional (loops over the whole file if omitted)
	print(reader.readout_number,np.max(reader.data))

reader.close_file()
```

You can also write data if you want:
```python
from ssdaq import SSDataReader
import numpy as np
writer = ssdaq.SSDataWriter('path/to/ssdata.hdf5')
for i in range(100):
	ro = ssdaq.SSReadout(i*10,i,np.random((32,64)),np.random((32,2),dtype=np.uint64))
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

* build docker image with:
	`docker build -t ss-sim .`
* setup your own docker network/bridge (Need to check command!)
	`docker network create --driver=bridge --subnet=192.168.0.0/16 br0`
* run container with TM sim:
	`docker run --net my-net --ip 172.18.0.1xx ss-sim`
the xx should be replaced by a number between 1 and 32 which corresponds to
the module number in the CHEC-camera

These commands might need to be prepended by sudo depending on how docker was installed on the machine. The network only needs to be created once while the `docker build` needs to be run everytime the simulation script to update the image.

To further make the handling of the simulation easier a small script,`docker-command.py` , that interfaces docker is provided. Starting a 32 module simulation is done by

`python tm-ss-sim/docker-command.py -r -N 32`

and can be stopped by

`python tm-ss-sim/docker-command.py -s`

more help is of course given by using the help option (`-h` or `--help`).
