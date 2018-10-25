# SSDAQ

Slow signal data acquisition and distribution for CHEC-S TARGET-C modules. 

This project contains a set of modules and scripts to receive slow signal data via UDP from TARGET-C modules (TM), build events from data recieved from multiple TMs and publish these  events on a tcp zmq PUB socket. There are also classes and scripts for receiving published event data and writing them to disk.


## Installation
#### Prerequisites

The project is written assuming it will be run with python3.5 or above. Additional dependencies to run the base part of the projects are listed here: 

* python >= 3.5
* numpy
* zmq

Some event receivers might have additional prerequesites not listed above. These dependencies include:

* pytables
* matplotlib
* urwid
* target_driver
* target_io
* target_calib

## Usage
The main usage is to run the `ssdaqd.py` which listens for data, build events out of the recieved data and publishes the events on a tcp socket. The program has a few options which will be printed if provided the `-h` option. A typical use case would be:

`python3 ssdaq/bin/ssdaqd.py -l LISTEN_PORT`

where the port which it should listen to incoming data is specified.

### Writing your own event receiver
The `SSEventListener` class provides an easy way to listen to the event stream generated by `ssdaqd.py`. Writing an event listener can be as simple as:

```python
from ssdaq.core import SSEventListener
port = "5555"
ev_list = SSEventListener.SSEventListener(port)
ev_list.start() #Starts listener thread
while(True):
    try:
    	# retreive event from event buffer (blocking call 
	# if block or timeout not specified see queue.Queue docs)
        event = ev_list.GetEvent()
    except :
        print("\nClosing listener")
        ev_list.CloseThread() 
        break
    #do stuff with event
```

The `try` statement around `event = ev_list.GetEvent()` makes it possible to exit the script gracefully by pressing `ctrl+C`. While handling the exception `CloseThread()` is called on the listener which sends a signal to the listener thread to finish and empties the event buffer. The event object (`SSEvent`) retreived from the `SSEventListener` is defined in `ssdaq/core/SSEventBuilder.py`.

### Simulating slow signal data from TMs
A python script that contains a simple simulation of the slow signal output from a TM is provided in this package in the folder `tm-ss-sim`.
To run it locally the following command can be used:

`python3 tm-ss-sim/SSUDPTMSimulator.py 2009 localhost`

which sets the simulation to send the data to port 2009 on localhost. For now the simulation sends ten readouts of random data that slowly fluctuates once per second. However, using this method only one TM can be simulated, but if docker containers are used for each TM then a complete camera can be simulated on a single laptop. 


#### Docker instructions to simulate multiple modules sending SS-data from the CHEC camera
This is just a summary of how to setup and use docker to simulate multiple TMs. (More documentation soon)

* build docker image with:
	`sudo docker build -t ss-sim .`
* setup your own docker network/bridge (Need to check command!)
	`docker network create --driver=bridge --subnet=192.168.0.0/16 br0`
* run container with TM sim
	`sudo docker run --net my-net --ip 172.18.0.1xx ss-sim`
the xx should be replaced by a number between 1 and 32 which corresponds to
the module number in the CHEC-camera
