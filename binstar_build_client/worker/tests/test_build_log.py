from __future__ import print_function, unicode_literals, absolute_import
import os
import string
import unittest

import mock

from binstar_build_client.worker.utils.build_log import BuildLog

class BSClient(object):
    def log_build_output(self, *args):
        self.last_log, self.last_tag, self.status = args[-3:]
        return False
    log_build_output_structured = log_build_output

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

        self.assertEqual(b'this can not be unicode \xe2', bs.last_log)
        self.assertEqual('start_build_on_worker', bs.last_tag)


    def test_read(self):
        with BuildLog(BSClient(), "un", "queue", "worker_id", 123, filename=self.filepath) as log:
            self.assertFalse(log.readable())

    def test_context(self):
        log = BuildLog(BSClient(), "un", "queue", "worker_id", 123, filename=self.filepath)
        self.assertFalse(log.fd.closed)
        with log:
            self.assertFalse(log.fd.closed)
        self.assertTrue(log.fd.closed)

    def test_section_breaks(self):
        for exit in (b'success', b'failure', b'error'):
            new_tag = lambda arg: BuildLog.SECTION_TAG + b' ' + arg
            bs = BSClient()
            log = BuildLog(bs, "un", "queue", "worker_id", 123, filename=self.filepath)
            for tag in (b'abc', b'def', b'ghi'):
                log.write(new_tag(tag))
                self.assertEqual(bs.last_log, new_tag(tag))
                self.assertEqual(bs.last_tag, tag)
                self.assertEqual(bs.status, '')
                log.write(b'info')
                self.assertEqual(bs.last_log, b'info')
            log.write(new_tag(b'exiting ' + exit))
            self.assertEqual(bs.status, exit)



if __name__ == '__main__':
    unittest.main()
