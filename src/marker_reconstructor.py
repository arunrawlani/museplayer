# Copyright 2015 InteraXon, Inc.
"""
Marker reconstruction.

This module is used by MatlabWriter to produce the markers struct in HDF5
files.
"""

import numpy as np

class MarkerReconstructor(object):
    """
    Converts a sequence of events to instances and markers.

    This does its best to reconstruct a sequence of markers with a beginning
    and end time and instances with a single time from a sequence of begins,
    ends, and instances with associated times.

    Markers can nest or overlap. In the case of nested/overlapping markers with
    the same name, where it can't otherwise be determined, they are always
    assumed to nest, i.e. <a 1><a 2></a 3></a 4> always leads to an outer a at
    [1, 4] and an inner a at [2, 3].

    Ends without beginnings have times represented as [-1, end_time].
    Beginnings without ends are represented as [start_time], i.e. a one-element
    array with just the beginning time.
    """
    def __init__(self):
        self._marker_name_to_start = dict()
        self._markers = list()
        self._instances = list()

    def add_instance(self, time, name):
        "Record an instantaneous event."
        self._instances.append({
            'type': 'Instance',
            'name': name,
            'times': [time],
        })

    def add_begin(self, time, name):
        "Record the start of a marker event."
        if not name in self._marker_name_to_start:
            self._marker_name_to_start[name] = []
        self._marker_name_to_start[name].append(time)

    def add_end(self, time, name):
        """
        Record the end of a marker event.

        If there is a corresponding beginning at time t without an end, then
        after this call, there is a marker with interval [t, time].

        If there is no corresponding beginning marker, then this call records a
        marker with a start time of -1.
        """
        if not name in self._marker_name_to_start:
            self._marker_name_to_start[name] = []
        start_times = self._marker_name_to_start[name]
        if not start_times:
            self._markers.append({
                'type': 'Marker',
                'name': name,
                'times': [-1, time]
            })
        else:
            last_start_time = start_times.pop()
            self._markers.append({
                'type': 'Marker',
                'name': name,
                'times': [last_start_time, time],
            })

    def markers(self):
        """
        Return the list of markers in struct-array form.

        What this produces should be interpreted by hdf5storage as a struct
        array. We represent the list of n items as a dict where each key is a
        list of n items.
        """
        ret_list = self._instances[:] + self._markers[:]
        for name, start_times in self._marker_name_to_start.items():
            for start_time in start_times:
                ret_list.append({
                    'type': 'Marker',
                    'name': name,
                    'times': [start_time],
                })
        def time_ordering(item):    # pylint:disable=missing-docstring
            if item['times'][0] < 0:
                return item['times'][-1]
            else:
                return item['times'][0]
        ret_sorted = sorted(ret_list, key=time_ordering)
        ret_rec = np.recarray((len(ret_sorted),),
                              dtype=[('type', 'O', (1,1)),
                                     ('name', 'O', (1,1)),
                                     ('times', 'O')])
        for i, x in enumerate(ret_sorted):
            name = np.asarray(x['name'], dtype=np.string_)
            ret_rec[i]['name'][0] = np.asarray(x['name'], dtype=np.string_)
            ret_rec[i]['times'] = np.asarray(x['times'])
            ret_rec[i]['type'][0] = np.asarray(x['type'], dtype=np.string_)
        return ret_rec
