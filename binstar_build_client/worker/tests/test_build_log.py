import os
import unittest

import mock

from binstar_build_client.worker.utils.build_log import BuildLog

class BSClient(object):
    def log_build_output(self, *args):
        return False

class TestBuildLog(unittest.TestCase):
    def setUp(self):
        self.filepath = os.path.join(os.getcwd(), 'build-log-test.txt')

    def tearDown(self):
        os.unlink(self.filepath)

    def test_write(self):
        with BuildLog(BSClient(), "un", "queue", "worker_id", 123, filename=self.filepath) as log:
            self.assertTrue(log.writable())
            res = log.write('test')
            self.assertEqual(len('test'), res)

    def test_read(self):
        with BuildLog(BSClient(), "un", "queue", "worker_id", 123, filename=self.filepath) as log:
            self.assertFalse(log.readable())

    def test_context(self):
        log = BuildLog(BSClient(), "un", "queue", "worker_id", 123, filename=self.filepath)
        self.assertFalse(log.fd.closed)
        with log:
            self.assertFalse(log.fd.closed)
        self.assertTrue(log.fd.closed)

if __name__ == '__main__':
    unittest.main()
