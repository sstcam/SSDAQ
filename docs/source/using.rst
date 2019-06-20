################################
Using SSDAQ for data acquisition
################################

The SSDAQ software package contains applications for CHEC-S pushed data acqusition and writing that data to disk, but can also be use as a python library to write custom subscribers, and to read and write slow signal, trigger, timestamp, log or monitoring data.

************
Applications
************

A range of applications are provided in the SSDAQ software package and if the install is sucessful these should all be in your path. The majority of the applications are different types of subscribers and the executables are prefixed with ``chec-<name>-<type>``, where ``<type>`` is the type of subscriber which will be explained shortly and ``<name>`` refers to the data which it subscribes to. Currently there are three types of subscribers, ``chec-dumpers`` which dump the content they receive directly in the terminal std output, ``chec-writer`` are as the name suggests subscribers that write to file and lastly we have the ``chec-daq-dash``, a simple terminal dash showing monitoring data from the receivers.

Starting and stopping the receivers should be done with the ``control-ssdaq`` application which starts the receivers as deamons and configures the logging so that it is output on a dedicated port. More on how to use `control-ssdaq` follows in the next section.

All the applications provide help options explaining the needed input.

Using ``control-ssdaq``
-----------------------
The ``control-ssdaq`` application manages the receiver and file writer daemons. The program consists of a number of commands and subcommands and each of the commands and subcommands provides a ``--help -h`` option and the top help message is shown here::

    Usage: control-ssdaq [OPTIONS] COMMAND [ARGS]...

      Start, stop and control receiver and writer daemons

    Options:
      -v, --version  Show version
      -h, --help     Show this message and exit.

    Commands:
      roa-ctrl  Send control commands to a running readout assembler daemon
      start     Start receivers or data writers
      stop      Stop a running receiver or writer daemon


The program provides two main commands `start` and `stop` for starting and stopping the daemons. Additionally there is the `roa-ctrl` command to send control commands to the readout assembler.

Start and stop receiver daemons
-------------------------------
The recommended way of starting the receivers is by using the command::

    control-ssdaq start daq

which starts all receivers that are configured in the default configuration. To start with a custom configuration one can specify a file with the ``--config, -c`` option. The ``start daq`` command also takes arguments that select which receivers to start `e.g`::

    control-ssdaq start daq Trigg Read

will only start the ``TriggerPacketReceiver`` and ``ReadoutAssembler``. Note that you only have to spell out enough of the receiver class name to make it unique. An empty arg list will start all receivers as seen earlier.

Receivers can be stopped in by using the `stop daq` command in the same manner that we started them, *i.e*::

    control-ssdaq stop daq

would stop all running receiver daemons while::

 control-ssdaq stop daq Trigg Read

would only stop the ``TriggerPacketReceiver`` and ``ReadoutAssembler`` daemons.

Start and stop filewriter daemons
---------------------------------
Currently only the `ReadoutFileWriter` daemon is supported and it is started with::

    control-ssdaq start dw  path/to/configfile.yaml -d
and stopped with::
    control-ssdaq stop dw

Note that if ``-d`` is ommited the writer will not run as a daemon, which can be good sometimes during testing, and output it's log messages directly in the terminal. To stop it type ``ctrl+C``.

List of receivers
-----------------

=====================  ========================================================================================
Receiver               Usage
=====================  ========================================================================================
ReadoutAssembler       Receives slow signal data from the FEE TMs and assembled them into a full camera readout
TriggerPacketReceiver  Receives trigger pattern packets from the backplane
TimestampReceiver      Recieves timestamps from the timing board
LogReceiver            Receives logs that are send on port `10001`
MonitorReceiver        Receives monitor data that is pushed on port `10002`
TelDataReceiver        Queries the ASTRI telescope database
=====================  ========================================================================================

List of standard port numbers used
----------------------------------

=====   ===================== ======================
Port    Usage                 Which application
=====   ===================== ======================
17000   "listen (UDP)"        ReadoutAssembler
8307    "listen (UDP)"        TriggerPacketReceiver
6666    "subscribe (TCP/ZMQ)" TimestampReceiver
9001    "publish  (TCP/ZMQ)"  LogReceiver
9002    "publish  (TCP/ZMQ)"  TriggerReceiver
9003    "publish  (TCP/ZMQ)"  TimestampReceiver
9004    "publish  (TCP/ZMQ)"  ReadoutAssembler
9005    "publish  (TCP/ZMQ)"  MonitorReceiver
9006    "publish  (TCP/ZMQ)"  TelDataReceiver
10001   "listen  (TCP/ZMQ)"   LogReceiver
10002   "pull  (TCP/ZMQ)"     MonitorReceiver
=====   ===================== ======================

*************
Configuration
*************



.. code-block:: yaml

    <ServerName>:
      Daemon:#Daemon configuration
        stdout: '/tmp/server.log'
        stderr: '/tmp/server.log'
        set_taskset: true #Using task set to force kernel not to swap cores
        core_id: 0 #which cpu core to use with taskset
      Receiver:#Receiver server configuration
        class: <ReceiverServerClass> #class defined in ssdaq.receivers
        listen_ip: 0.0.0.0
        listen_port: 17000
        #Server specific arguments go here
      Publishers: #Listing publishers
        <PublisherName>: #name
          class: ZMQTCPPublisher #class defined in ssdaq.core.publishers
          ip: 127.0.0.101
          port: 9004


.. code-block:: yaml

    <WriterName>:
      Daemon:
        #redirection of output (should be /dev/null when logging is fully configurable)
        stdout: '/path/to/writer.log'
        stderr: '/path/to/writer.log'
      Writer:
        class: <WriterClass>
        file_enumerator: date #enumerates with timestamp (yr-mo-dy.H:M) or `order` which enumerates with numbers starting from 00001
        file_prefix: FileNamePrefix
        folder: /path/to/folder
        ip: 127.0.0.101
        port: 9004
        filesize_lim: 600


Configure location of config files
----------------------------------
``control-ssdaq`` will look for a file called ``.ssdaq_config.yaml`` in the home folder in which ``writer-config`` sets the location of the location of the writer configuration file and ``daq-config`` sets the location of the configuration of the receiver servers.

