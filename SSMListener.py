import socket
import os
import numpy as np
import struct

class SSListener(object):
	def __init__(self, port):
		self.port = port


if (__name__ == "__main__"):
	import sys
	port = int(sys.argv[1])

	# Create a TCP/IP socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# Bind the socket to the port
	server_address = ('0.0.0.0', port)
	print >>sys.stderr, 'starting up on %s port %s' % server_address
	sock.bind(server_address)
	
	format_str10 = ''
	for i in range(10):
		format_str10 += 'Q32H'+'Q32H'
	format_str11 = format_str10 + 'Q32H'+'Q32H'
	print(format_str10)
	npackets = {}
	npackets_tot = 0
	while(True):
		data, address = sock.recvfrom(6096)
		# print(data,address)
		print()
		print("#############################")
		print("Address: %s"%(str(address)))
		print(len(data))
		print("Data:")
		# data_dict = {}
		# data_list = struct.unpack(format_str10,data)
		# for d in :

		# 	data_dict
		for i in range(10):
			print('Readout ',i, struct.unpack_from('Q32H'+'Q32H',data,i*(64*2+2*8)))
		# print(struct.unpack_from(format_str10,data,i*33*8))
		npackets_tot +=1
		if(npackets.has_key(address[0])):
			npackets[address[0]] +=1
		else:
			npackets[address[0]] =1

		if(npackets_tot%20==0):
			for k,v in npackets.iteritems():
				print("Received %d packets from %s"%(v,k))

			print("Total packets received %d"%(npackets_tot))