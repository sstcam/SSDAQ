# Use an official Python runtime as a parent image
FROM python:3.6-alpine3.7

RUN apk --no-cache add --virtual .builddeps gcc gfortran musl-dev     && pip install numpy==1.14.0     && apk del .builddeps     && rm -rf /root/.cache
# extra metadata
LABEL version="1.2"
LABEL description="Docker file for TM simulation."

# setup working directory
ADD tm-ss-sim /app
WORKDIR /app

# expose port
EXPOSE 2009

# start app
CMD [ "python", "./SSUDPTMSimulator.py","2009" ]