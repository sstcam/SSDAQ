###########
Subscribers
###########
The subscriber classes are intended as a common interface to the published
data on zmq sockets from the ReceiverServers. These subscribers come in two flavors:
the :py:class:`ssdaq.core.BasicSubscriber`, which under the hood uses a separate thread
to listen to and buffer the published data stream. This buffer can be later accessed via
a blocking call to :py:meth:`ssdaq.core.BasicSubscriber.get_data`, which makes the class
easy to use, however combining multiple subscribers asynchronously in one process is
quite cumbersome. The :py:class:`ssdaq.core.AsyncSubscriber` instead designed to be used in
an asynchronous context by running it in an :py:mod:`asyncio` eventloop. The
:py:meth:`ssdaq.core.AsyncSubscriber.get_data` is therefore a coroutine. Having several
:py:class:`ssdaq.core.AsyncSubscriber` subscribers running asynchronously in an application
is simply a matter of adding them to the to the eventloop of that application.

****************
Base Subscribers
****************

ssdaq.core.BasicSubscriber
==========================
.. autoclass:: ssdaq.core.BasicSubscriber
    :members:

Examples
--------
A simple raw listener::

    from ssdaq.core import BasicSubscriber
    sub = BasicSubscriber(port = 5555, ip ='127.0.0.1')
    sub.start() #Starts listener thread
    while(True):
        try:
            # retrieve data buffer (blocking call
            # if block or timeout not specified see queue.Queue docs)
            data = sub.get_data()
            #if the data is of type 'None' the listener thread has been closed.
        if(readout == None):
            break
        except :
            print("\nClosing listener")
            sub.close()
            break

Deriving a subscriber for a specific data type::

    from ssdaq.core import BasicSubscriber
    from mymodule import MyData
    class MyDataSubscriber(BasicSubscriber):
    def __init__(self, ip: str, port: int, logger: logging.Logger = None):
        super().__init__(ip=ip, port=port, logger=logger, unpack=MyData.unpack)

ssdaq.core.AsyncSubscriber
==========================

.. autoclass:: ssdaq.core.AsyncSubscriber
    :members:

Examples
--------
A simple raw listener::

    import asyncio
    from ssdaq.core import AsyncSubscriber
    loop = asyncio.get_event_loop()
    sub = AsyncSubscriber(ip="127.0.0.1",port =5555)

    async def print_data(loop, sub):
        running = True
        while running:
            try:
                data = await sub.get_data()
                print(data)
                if data is None:
                    running = False
                    close = loop.create_task(sub.close())
                    close.add_done_callback(lambda x: loop.stop())
            except asyncio.CancelledError:
                print("Exit")
                return


    task = loop.create_task(print_data(loop, sub))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print()
        if not task.cancelled():
            task.cancel()

        loop.run_until_complete(sub.close(True))

WriterSubscribers
=================

.. autoclass:: ssdaq.core.AsyncWriterSubscriber
    :members:


.. autoclass:: ssdaq.core.WriterSubscriber
    :members:




Derived Subscribers
===================


.. inheritance-diagram:: ssdaq.subscribers
   :parts: 1

.. graphviz::

   digraph {
      AsyncSubscriber [shape=box];
      BaseFileWriter [shape=box];
      RawObjectWriterBase [shape=box];
      AsyncWriterSubscriber [shape=box];
      "Async<Type>Subscriber" [shape=box];
      "<Type>Writer" [shape=box];
      "Async<Type>WriterSubscriber" [shape=box];
      AsyncSubscriber ->"Async<Type>Subscriber";
      BaseFileWriter -> AsyncWriterSubscriber ;
      AsyncSubscriber -> AsyncWriterSubscriber [style=dotted] ;
      RawObjectWriterBase ->AsyncWriterSubscriber [style=dotted] ;
      RawObjectWriterBase -> "<Type>Writer" ;
      AsyncWriterSubscriber -> "Async<Type>WriterSubscriber" ;
      "Async<Type>Subscriber"-> "Async<Type>WriterSubscriber" [style=dotted] ;
      "<Type>Writer"-> "Async<Type>WriterSubscriber" [style=dotted] ;
   }

Listing derived subscribers
---------------------------

.. automodule:: ssdaq.subscribers
    :members: