from __future__ import print_function, unicode_literals, absolute_import
import os
import unittest

import mock

from binstar_build_client.worker.utils.build_log import BuildLog

class BSClient(object):
    def log_build_output(self, *args):
        self.last_log = args[-1]
        return False

class TestBuildLog(unittest.TestCase):
    def setUp(self):
        self.filepath = os.path.join(os.getcwd(), 'build-log-test.txt')

    def tearDown(self):
        os.unlink(self.filepath)

    def test_write(self):

        log = BuildLog(BSClient(), "un", "queue", "worker_id", 123, filename=self.filepath)

        with log:
            self.assertTrue(log.writable())
            res = log.write(b'test')
            self.assertEqual(4, res)

            with self.assertRaises(TypeError):
                log.write('this is unicode')

    def test_write_invalid_unicode(self):

        bs = BSClient()
        log = BuildLog(bs, "un", "queue", "worker_id", 123, filename=self.filepath)

        with log:
            log.write(b'this can not be unicode \xe2')

        self.assertIn('this can not be unicode', bs.last_log)


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
