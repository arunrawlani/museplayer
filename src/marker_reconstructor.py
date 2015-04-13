# Copyright 2015 InteraXon, Inc.

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
    """
    def __init__(self):
        self._marker_name_to_start = dict()
        self._markers = list()
        self._instances = list()

    def add_instance(self, time, name):
        "Record an instantaneous event."
        self._instances.append({
            'type': 'instance',
            'name': name,
            'times': [time],
        })

    def add_begin(self, time, name):
        "Record the start of a marker event."
        if not name in self._marker_name_to_start:
            self._marker_name_to_start[name] = []
        self._marker_name_to_start[name].append(time)

    def add_end(self, time, name):
        "Record the end of a marker event."
        if not name in self._marker_name_to_start:
            self._marker_name_to_start[name] = []
        start_times = self._marker_name_to_start[name]
        if not start_times:
            self._markers.append({
                'type': 'marker',
                'name': name,
                'times': [-1, time]
            })
        else:
            last_start_time = start_times.pop()
            self._markers.append({
                'type': 'marker',
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
                    'type': 'marker',
                    'name': name,
                    'times': [start_time],
                })
        def time_ordering(item):
            if item['times'][0] < 0:
                return item['times'][-1]
            else:
                return item['times'][0]
        ret_sorted = sorted(ret_list, key=time_ordering)
        return {
            'type': [x['type'] for x in ret_sorted],
            'name': [x['name'] for x in ret_sorted],
            'times': [x['times'] for x in ret_sorted]
        }
