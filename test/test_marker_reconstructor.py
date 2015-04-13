import unittest

import marker_reconstructor

class MarkerReconstructorTest(unittest.TestCase):
    def setUp(self):
        self.reconstructor = marker_reconstructor.MarkerReconstructor()

    def assertIsObjects(self, objects, markers=None):
        if not markers:
            markers = self.reconstructor.markers()
        self.assertEqual(len(objects), len(markers))
        for i, object in enumerate(objects):
            self.assertEqual(object[0], markers[i]['type'])
            self.assertEqual(object[1], markers[i]['name'])
            self.assertEqual(len(object[2]), len(markers[i]['times']))
            for j, t in enumerate(object[2]):
                self.assertEqual(t, markers[i]['times'][j])

    def test_reconstruct_none(self):
        output = self.reconstructor.markers()
        self.assertEqual(0, len(output))

    def test_reconstruct_begin(self):
        self.reconstructor.add_begin(3.14, 'test')
        output = self.reconstructor.markers()
        self.assertEqual(1, len(output))
        self.assertEqual('Marker', output[0]['type'])
        self.assertEqual('test', output[0]['name'])
        self.assertEqual([3.14], output[0]['times'])

    def test_reconstruct_begin_end(self):
        self.reconstructor.add_begin(3.2, 'foo')
        self.reconstructor.add_end(3.3, 'foo')
        output = self.reconstructor.markers()
        self.assertEqual(1, len(output))
        self.assertEqual('Marker', output[0]['type'])
        self.assertEqual('foo', output[0]['name'])
        self.assertEqual(3.2, output[0]['times'][0])
        self.assertEqual(3.3, output[0]['times'][1])

    def test_reconstruct_begin_begin(self):
        self.reconstructor.add_begin(1, 'bob')
        self.reconstructor.add_begin(512, 'dole')
        output = self.reconstructor.markers()
        self.assertIsObjects(
            [('Marker', 'bob', [1]),
             ('Marker', 'dole', [512])])

    def test_reconstruct_end_end(self):
        self.reconstructor.add_end(1, 'baz')
        self.reconstructor.add_end(2, 'baz')
        output = self.reconstructor.markers()
        self.assertIsObjects(
            [('Marker', 'baz', [-1, 1]),
             ('Marker', 'baz', [-1, 2])])

    def test_reconstruct_a_b_a(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'b')
        self.reconstructor.add_end(3, 'a')
        self.assertIsObjects(
            [('Marker', 'a', [1, 3]),
             ('Marker', 'b', [2])])

    def test_reconstruct_a_b_b(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'b')
        self.reconstructor.add_end(3, 'b')
        self.assertIsObjects(
            [('Marker', 'a', [1]),
             ('Marker', 'b', [2, 3])])

    def test_nested(self):
        self.reconstructor.add_begin(1, 'b')
        self.reconstructor.add_begin(2, 'a')
        self.reconstructor.add_end(3, 'a')
        self.reconstructor.add_end(4, 'b')
        self.assertIsObjects(
            [('Marker', 'b', [1, 4]),
             ('Marker', 'a', [2, 3])])

    def test_overlapping(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'b')
        self.reconstructor.add_end(3, 'a')
        self.reconstructor.add_end(4, 'b')
        self.assertIsObjects(
            [('Marker', 'a', [1, 3]),
             ('Marker', 'b', [2, 4])])

    def test_instances(self):
        self.reconstructor.add_instance(5123.5, 'wut')
        self.assertIsObjects(
            [('Instance', 'wut', [5123.5])])

    def test_instances_markers(self):
        self.reconstructor.add_instance(1, 'wut')
        self.reconstructor.add_begin(2, 'tsst')
        self.reconstructor.add_end(3, 'tsst')
        self.reconstructor.add_begin(4, 'abc')
        self.reconstructor.add_end(5, 'abc')
        self.reconstructor.add_begin(6, 'abc')
        self.reconstructor.add_end(7, 'def')
        self.assertIsObjects(
            [('Instance', 'wut',  [1]),
             ('Marker',   'tsst', [2, 3]),
             ('Marker',   'abc',  [4, 5]),
             ('Marker',   'abc',  [6]),
             ('Marker',   'def',  [-1, 7])])

    def test_same_nested(self):
        self.reconstructor.add_begin(1, 'a')
        self.reconstructor.add_begin(2, 'a')
        self.reconstructor.add_end(4, 'a')
        self.reconstructor.add_end(5, 'a')
        self.assertIsObjects(
            [('Marker', 'a', [1, 5]),
             ('Marker', 'a', [2, 4])])

    def test_multiple_markers_calls(self):
        self.reconstructor.add_instance(1, 'abc')
        self.reconstructor.add_begin(2, 'def')
        self.reconstructor.add_begin(3, 'fgh')
        self.reconstructor.add_end(4, 'fgh')
        self.assertIsObjects(
            [('Instance', 'abc', [1]),
             ('Marker',   'def', [2]),
             ('Marker',   'fgh', [3, 4])])
        self.assertIsObjects(
            [('Instance', 'abc', [1]),
             ('Marker',   'def', [2]),
             ('Marker',   'fgh', [3, 4])])
