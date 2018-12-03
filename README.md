# SSDAQ 
![Test Status Travis-CI](https://travis-ci.org/sflis/SSDAQ.svg?branch=master) [![Coverage Status](https://coveralls.io/repos/github/sflis/SSDAQ/badge.svg?branch=master)](https://coveralls.io/github/sflis/SSDAQ?branch=master)

Slow signal data acquisition and distribution for CHEC-S TARGET-C modules. 

This project contains a set of modules and scripts to receive slow signal data via UDP from TARGET-C modules (TM), build events from data recieved from multiple TMs and publish these  events on a tcp zmq PUB socket. There are also classes and scripts for receiving published event data and writing them to disk.


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

Some event receivers might have additional prerequesites not listed above. These dependencies include:

* matplotlib
* docker
* urwid
* target_driver
* target_io
* target_calib

## Usage
The main usage of this software package is to run the `ssdaqd` application which listens for data, build events out of the recieved data and publishes the events on a tcp socket. The program has a few options which will be printed if provided the `-h` option. A typical use case would be:

`ssdaq -l LISTEN_PORT`

where the port which it should listen to incoming data is specified.

Below follows a list of all the applications that are provided by SSDAQ:

* `ssdaq`
* `ssdatawriter`
* `ss-example-listener`
* `control-ssdaq`

### Using ssdatawriter

### Using control-ssdaq

### Writing your own event receiver
The `SSEventListener` class provides an easy way to listen to the event stream generated by `ssdaqd.py`. Writing an event listener can be as simple as:

```python
from ssdaq import SSEventListener
port = "5555"
ev_list = SSEventListener(port)
ev_list.start() #Starts listener thread
while(True):
    try:
    	# retreive event from event buffer (blocking call 
	# if block or timeout not specified see queue.Queue docs)
        event = ev_list.GetEvent()
    	#if the event is of type 'None' the listener thread has been closed.
	if(event == None):
	    break 
    except :
        print("\nClosing listener")
        ev_list.CloseThread() 
        break
    #do stuff with event
```

The `try` statement around `event = ev_list.GetEvent()` makes it possible to exit the script gracefully by pressing `ctrl+C`. While handling the exception `CloseThread()` is called on the listener which sends a signal to the listener thread to finish and empties the event buffer. The event object (`SSEvent`) retreived from the `SSEventListener` is defined in `ssdaq/core/ss_event_builder.py`.

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
