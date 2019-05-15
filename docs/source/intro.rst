Introduction
============

This project can be eiter used as a collection of applications that constitute the data acqusition system (DAQ) for pushed data from the CHEC-S camera (whith the exception of cherenkow data) including publishers and subscribers to these data. However this document will focus on the library API and the project structure, which can be used to interface the DAQ components as well as writing and reading data.

The SSDAQ package contains the following main components:

* Data format definitions
    * IO tools for the data
* **Receivers** (mainly to receive pushed data from CHEC)
* **Subscribers** (that can subscribe to published data streams from the **Receivers**)

The file structure of the pro
