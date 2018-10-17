from ssdaq.SSDataListener import SSDataListener
from ssdaq.SSEventBuilder import SSEventBuilder
from ssdaq.SSEventDataPublisher import SSEventDataPublisher

import sys
import time
listen_port = sys.argv[1]
publicate_port = sys.argv[2]
eb = SSEventBuilder()
dl = SSDataListener(listen_port,eb.data_queue)
ep = SSEventDataPublisher(publicate_port,eb.event_queue)

dl.start()
time.sleep(1)
eb.start()
time.sleep(1)
ep.start()
