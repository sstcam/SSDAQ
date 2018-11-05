from threading import Thread
import zmq
import logging

class SSEventDataPublisher(Thread):
    def __init__(self,port,event_queue):
        Thread.__init__(self)
        self.event_queue = event_queue
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.PUB)
        con_str = 'tcp://127.0.0.101:'+str(port)
        self.sock.bind(con_str)
        self.running = False
        self.log = logging.getLogger('ssdaq.SSEventDataPublisher')
        self.log.info('Initialized event publisher on: %s'%con_str)

    def run(self):
        self.running = True
        self.setName('SSEventDataPublisher')
        self.log.info('Starting event publishing thread')
        while(self.running):
            event = self.event_queue.get()
            self.sock.send(event.pack())

