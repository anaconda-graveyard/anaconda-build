from __future__ import print_function
import unittest

from gevent_io import main


class TestGeventIO(unittest.TestCase):

    def test_finishes(self):
        out = main('echo ok1;sleep 5; echo ok2', 200, 60)
        self.assertIn('ok1', out)
        self.assertIn('ok2', out)
        self.assertNotIn('timeout', out)

    def test_times_out(self):
        out = main('echo ok1;sleep 20; echo ok2', 5, 60)
        self.assertIn('ok1', out)
        self.assertNotIn('ok2', out)
        self.assertIn('timeout', out)
        self.assertNotIn('iotimeout', out)

    def test_io_times_out(self):
        out = main('echo ok1; sleep 20; echo ok2', 200, 5)
        self.assertIn('ok1', out)
        self.assertIn('iotimeout', out)
        self.assertNotIn('ok2', out)