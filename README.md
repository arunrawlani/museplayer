MusePlayer
===========
-----------

MusePlayer is a utility for recording, replaying, rerouting, and converting EEG 
and accelerometer data from Interaxon Muse EEG devices. It can save to and 
convert between the native Muse datatype (.muse), Matlab (HDF5), CSV, and OSC 
replay formats. 

####Supported Inputs

- OSC network stream
- OSC-replay file format
- Muse file format v1
- Muse file format v2


####Supported Outputs

- MATLAB (HDF5)
- CSV
- OSC network stream
- OSC-replay file format
- Muse file format v2
- Print to screen

Usage
=====
-----

MusePlayer takes Muse data in a variety of formats and then outputs Muse data in a variety of formats. For example:

    muse-player -l 5000 -M path/to/recording/muse_recording.mat

Listens for Muse OSC data over TCP on port 5000, and records it to a MATLAB file in path/to/recording/muse_recording.mat

For more information on all the options for MusePlayer including message filtering options, type "muse-player" in your shell to see the help docs.



Dependencies  
============
------------

- [PyInstaller](https://github.com/pyinstaller/pyinstaller/wiki) - to build the all-in-one executable

####C libraries

- [liblo](http://liblo.sourceforge.net/)       - for OSC reading/writing
- [libhdf5](http://www.hdfgroup.org/HDF5/release/obtain5.html)     - for reading/writing HDF5 matlab files

####Python libraries

- [pyliblo](http://das.nasophon.de/pyliblo/)     - python bindings for liblo
- [scipy](http://www.scipy.org/)       - for reading/writing HDF5 matlab files 
- [numpy](http://www.numpy.org/)      - for reading/writing HDF5 matlab files
- [Google Protocol Buffers](https://developers.google.com/protocol-buffers/)    - for reading/writing .muse files
- [h5py](http://www.h5py.org/)    - python bindings for libhdf5

#####Testing Dependencies

- [mock](https://pypi.python.org/pypi/mock)
- [nose](https://nose.readthedocs.org/en/latest/)     

Building
========
--------

MusePlayer is built with [PyInstaller](https://github.com/pyinstaller/pyinstaller/wiki). Build scripts are under scripts/. E.g.

    scripts/build.sh

to build the all-in-one executable. 


Testing
=======
-------

The main test script is /scripts/test.py. You will need to install [mock](https://pypi.python.org/pypi/mock) and [nose](https://nose.readthedocs.org/en/latest/) to run it.

MusePlayer is tested by inputting known test data and checking the output against golden examples of correct output data for each configuration. All test data
is stored in the test_data directory.


Contributing
============
------------

To contribute code to the MusePlayer project, you must follow the standard fork and pull request workflow. For details on this 
process as well as how to submit bug reports and feature requests, see the CONTRIBUTE file.


License
======
------

MusePlayer is licensed under the provisions of the MIT license. See the LICENSE file for details.
