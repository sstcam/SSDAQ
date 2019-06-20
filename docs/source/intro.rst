############
Introduction
############

This project can be eiter used as a collection of applications that constitute the data acqusition system (DAQ) for pushed data from the CHEC-S camera (whith the exception of the fast Cherenkow data) including publishers and subscribers to these data or as a library to read the data written by the DAQ components.

.. However this document will focus on the library API and the project structure, which can be used to interface the DAQ components as well as writing and reading data.

The SSDAQ package contains the following main components:

* Data format definitions
    * IO tools for the data: readers and writers for the different types of data
* **Receivers** (mainly to receive pushed data from CHEC)
* **Subscribers** (that can subscribe to published data streams from the **Receivers**)
* Applications for:
    * controlling receiver and writer daemons
    * subscribing to published data

**Here references should go to different sections**

Data Acquisition Architecture
=============================

The following diagram shows the data acquisition setup of SSDAQ. A Receiver-server running on the camera server is receiving pushed data from the camera or some other device and publishes the data on a zmq socket that a Subscriber and a WriterSubscriber subscribes to. The rectangles in this diagram represent servers while the pentagons represent client subscribers.

.. graphviz::

   digraph {
        "Camera/Device" [shape=box3d];
        "Receiver-server"      [shape=box];
        "Subscriber"    [shape=pentagon];
        "WriterSubscriber"    [shape=box];
        "file" [shape=cylinder];
        "LogReceiver"   [shape=box];
        "MonitorReceiver"   [shape=box];
        "LogSubscriber"   [shape=pentagon];
        "MonSubscriber"   [shape=pentagon];
        edge [style=bold];
        "Camera/Device" -> "Receiver-server";
        "Receiver-server" -> {"Subscriber","WriterSubscriber"};
        "WriterSubscriber" -> "file";

        "MonitorReceiver" -> "MonSubscriber";
        "LogReceiver" -> "LogSubscriber";
        edge [color=gray];
        edge [style=solid];
        "Camera/Device" -> "MonitorReceiver" [label="planned"];
        "Camera/Device" -> "LogReceiver" [label="planned"];
        edge [color=black];
        "MonitorReceiver" -> "MonitorReceiver"  [style=dotted];
        "MonitorReceiver" -> "LogReceiver"  [style=dashed];
        "Receiver-server" -> "MonitorReceiver" [style=dotted];
        "Receiver-server" -> "LogReceiver" [style=dashed];
        { rank = same; "Receiver-server"; "LogReceiver"; "MonitorReceiver"; }
   }
Additionally two internal Receiver-servers are shown, namely the  ``MonitorReceiver`` and ``LogReceiver``, which collect monitoring and log data, respectively, from the other running servers. In the future it might possible that the monitoring data as well as logs from the Camera and other components such as the camera server might be pushed to these receivers.


Project structure
=================