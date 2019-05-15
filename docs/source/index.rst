.. SSDAQ documentation master file, created by
   sphinx-quickstart on Tue May 14 16:52:36 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
=================================
Welcome to SSDAQ's documentation!
=================================
This project contains a set of modules and applications that receive and handle pushed data from the CHEC-S camera. Definitions of the pushed data formats and tools to write and read the data to disk are provided. The data processed by the receivers can then published on TCP sockets that are subscribable. Subscribers for printing out the data or writing it to disk are provided as well.


.. toctree::
    data
    recv
    subs
    :maxdepth: 2
..   Receivers
   Subscribers
   Data

   :caption: Contents:

Introduction
============

This project can be eiter used as a collection of applications that constitute the data acqusition system (DAQ) for pushed data from the CHEC-S camera (whith the exception of cherenkow data) including publishers and subscribers to these data. However this document will focus on the library API and the project structure, which can be used to interface the DAQ components as well as writing and reading data.

The SSDAQ package contains the following main components:

* Data format definitions
    * IO tools for the data
* **Receivers** (mainly to receive pushed data from CHEC)
* **Subscribers** (that can subscribe to published data streams from the **Receivers**)

The file structure of the pro



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
