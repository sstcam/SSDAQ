#########
Receivers
#########



ssdaq.core.ReceiverServer
=========================
Receivers should inherit from the ``ReceiverServer`` class in order to be started with
the `control-ssdaq` application. The class contains functionality to open a TCP or UDP
listenting sockets using asyncio. Methods prefixed with ``ct_`` must be coroutines and will
be added once to the event loop when the ``run()`` method is called. The ``ReceiverServer``
class also implements a command receiver server. Callbacks methods for the commands are prefixed
with ``cmd_``.

.. autoclass:: ssdaq.core.ReceiverServer
    :members:

Example of a receiver listening to a UDP socket
-----------------------------------------------
The following code example shows the typical way to set up
a receiver in SSDAQ that listens to a UDP socket and later
publishes the packets::
    import asyncio
    from ssdaq.core.receiver_server import ReceiverServer
    from .mon_sender import ReceiverMonSender
    class PacketProtocol(asyncio.Protocol):
        def __init__(self, loop, log):
            self.buffer = asyncio.Queue()
            self.loop = loop
            self.log = log.getChild("PacketProtocol")

        def connection_made(self, transport):
            self.log.info("Connected to port")
            self.transport = transport

        def datagram_received(self, data, addr):
            self.buffer.put_nowait((data, addr))


    class PacketReceiver(ReceiverServer):
        def __init__(self, ip: str, port: int, publishers: list):
            super().__init__(ip, port, publishers, "PacketReceiver")
            self.trans, self.tpp = self.setup_udp(
                lambda: PacketProtocol(self.loop, self.log)
            )
            self.running = True
            # To send basic monitoring data a ReceiverMonSender instance is needed
            self.mon = ReceiverMonSender("PacketReceiver", self.loop, self._context)
        # This method will be automatically added to as a task to the
        # asyncio eventloop
        async def ct_relay(self):
            while self.running:
                packet = await self.tpp.buffer.get()
                # Need to register each time we get a packet
                # The ReceiverMonSender automatically calculates the
                # rate and pushes the monitoring data to a monitor receiver
                self.mon.register_data_packet()
                await self.publish(packet[0])


ssdaq.receivers
===============
.. automodule:: ssdaq.receivers.ReadoutAssembler
    :members: