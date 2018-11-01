# Use an official Python runtime as a parent image
FROM python:3.6-alpine3.7

RUN apk --no-cache add --virtual .builddeps gcc gfortran musl-dev  && apk add build-base libzmq  python3-dev zeromq-dev && pip3 install pyzmq  && pip install numpy==1.14.0     && apk del .builddeps     && rm -rf /root/.cache
# extra metadata
LABEL version="1.2"
LABEL description="Docker file for TM simulation."

# setup working directory
ADD SSUDPTMSimulator.py /app/
WORKDIR /app

# expose port
EXPOSE 2009/udp
EXPOSE 30001

# start app
#CMD [ "python3", "./SSUDPTMSimulator.py", "-d","2009" , "-i","172.17.0.1","-m","$MY_IP","-c","$COM_PORT","-t","$TM_ID" ]
CMD python3 ./SSUDPTMSimulator.py -d 2009 -i 172.17.0.1 -m $MY_IP -c 30001 -t $TM_ID