import unittest

import marker_reconstructor

class MarkerReconstructorTest(unittest.TestCase):
    def setUp(self):
        self.reconstructor = marker_reconstructor.MarkerReconstructor()

    def test_reconstruct_none(self):
        output = self.reconstructor.markers()
        self.assertEqual(output, {
            'type': [],
            'name': [],
            'times': [],
        })

    def test_reconstruct_begin(self):
        self.reconstructor.add_begin(3.14, 'test')
        output = self.reconstructor.markers()
        self.assertEqual(output, {
            'type': ['marker'],
            'name': ['test'],
            'times': [[3.14]],
        })

    def test_reconstruct_begin_end(self):
        self.reconstructor.add_begin(3.2, 'foo')
        self.reconstructor.add_end(3.3, 'foo')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker'],
            'name': ['foo'],
            'times': [[3.2, 3.3]],
        })

    def test_reconstruct_begin_begin(self):
        self.reconstructor.add_begin(1, 'bob')
        self.reconstructor.add_begin(512, 'dole')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['bob', 'dole'],
            'times': [[1], [512]],
        })

    def test_reconstruct_end_end(self):
        self.reconstructor.add_end(1, 'baz')
        self.reconstructor.add_end(2, 'baz')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['baz', 'baz'],
            'times': [[-1, 1], [-1, 2]],
        })

    def test_reconstruct_a_b_a(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'b')
        self.reconstructor.add_end(3, 'a')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['a', 'b'],
            'times': [[1, 3], [2]],
        })

    def test_reconstruct_a_b_b(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'b')
        self.reconstructor.add_end(3, 'b')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['a', 'b'],
            'times': [[1], [2, 3]],
        })

    def test_nested(self):
        self.reconstructor.add_begin(1, 'b')
        self.reconstructor.add_begin(2, 'a')
        self.reconstructor.add_end(3, 'a')
        self.reconstructor.add_end(4, 'b')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['b', 'a'],
            'times': [[1, 4], [2, 3]],
        })

    def test_overlapping(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'b')
        self.reconstructor.add_end(3, 'a')
        self.reconstructor.add_end(4, 'b')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['a', 'b'],
            'times': [[1, 3], [2, 4]],
        })

    def test_instances(self):
        self.reconstructor.add_instance(5123.5, 'wut')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['instance'],
            'name': ['wut'],
            'times': [[5123.5]],
        })

    def test_instances_markers(self):
        self.reconstructor.add_instance(1, 'wut')
        self.reconstructor.add_begin(2, 'tsst')
        self.reconstructor.add_end(3, 'tsst')
        self.reconstructor.add_begin(4, 'abc')
        self.reconstructor.add_end(5, 'abc')
        self.reconstructor.add_begin(6, 'abc')
        self.reconstructor.add_end(7, 'def')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['instance', 'marker', 'marker', 'marker', 'marker'],
            'name': ['wut',      'tsst',   'abc',    'abc',    'def'],
            'times': [[1],       [2, 3],   [4, 5],   [6],      [-1, 7]],
        })

    def test_same_nested(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'a')
        self.reconstructor.add_end(4, 'a')
        self.reconstructor.add_end(5, 'a')
        self.assertEqual(self.reconstructor.markers(), {
            'type': ['marker', 'marker'],
            'name': ['a', 'a'],
            'times': [[1, 5], [2, 4]],
        })

    def test_multiple_markers_calls(self):
        self.reconstructor.add_instance(1, 'abc')
        self.reconstructor.add_begin(2, 'def')
        self.reconstructor.add_begin(3, 'fgh')
        self.reconstructor.add_end(4, 'fgh')
        self.assertEqual(self.reconstructor.markers(),
                         self.reconstructor.markers())
