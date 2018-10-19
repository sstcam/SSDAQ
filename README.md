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

* matplotlib
* urwid
* target_driver
* target_io
* target_calib

## Usage


### Writing your on event receiver


### Simulating slow signal data from TMs


#### Docker instructions to simulate multiple modules sending SS-data from the CHEC camera

* build docker image with:
	`sudo docker build -t ss-sim .`
* setup your own docker network/bridge (Need to check command!)
	`docker network create --driver=bridge --subnet=192.168.0.0/16 br0`
* run container with TM sim
	`sudo docker run --net my-net --ip 172.18.0.1xx ss-sim`
the xx should be replaced by a number between 1 and 32 which corresponds to
the module number in the CHEC-camera
