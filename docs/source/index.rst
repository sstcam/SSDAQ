.. SSDAQ documentation master file, created by
   sphinx-quickstart on Tue May 14 16:52:36 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
=================================
Welcome to SSDAQ's documentation!
=================================
This project contains a set of modules and applications that receive and handle pushed data from the CHEC-S camera. Definitions of the pushed data formats and tools to write and read the data to disk are provided. The data processed by the receivers can then published on TCP sockets that are subscribable. Subscribers for printing out the data or writing it to disk are provided as well.



Installation
============
For a normal install run

``python setup.py install``

or in the root directory of the project do

``pip install .``

If you are developing it is recommendended to do

``pip install -e .``

instead and adding the ``--user`` option if not installing in a conda env. This lets changes made to the project automatically propagate to the install without the need to reinstall.

..   Receivers
   Subscribers
   Data

   :caption: Contents:
Table of contents
=================
.. toctree::
    intro
    data
    recv
    subs
    ref/ssdaq
    :maxdepth: 2

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
