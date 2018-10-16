# SSDAQ
Slow signal data acquisition and distribution for CHEC-S TARGET-C modules.


* Docker instructions to simulate multiple modules sending SS-data from the CHEC camera

build docker image with:
	sudo docker build -t ss-sim .
setup your own docker network/bridge (Need to check command!)
	docker network create --driver=bridge --subnet=192.168.0.0/16 br0
run container with TM sim
	sudo docker run --net my-net --ip 172.18.0.1xx ss-sim
the xx should be replaced by a number between 1 and 32 which corresponds to
the module number in the CHEC-camera