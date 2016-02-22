from __future__ import print_function, unicode_literals, absolute_import
import os
import string
import unittest
from six.moves import urllib

import mock
from binstar_client.tests.urlmock import urlpatch
from binstar_client.tests import urlmock

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.utils import build_log
from binstar_build_client.worker.utils.build_log import BuildLog


class TestBuildLog(unittest.TestCase):

    def add_log_entry(self, request):
        log = dict(urllib.parse.parse_qsl(request.body))
        self.log_entries.append(log)

    def setUp(self):
        self.filepath = os.path.join(os.getcwd(), 'build-log-test.txt')
        self.log_entries = []
        self.urls = urlmock.Registry()
        self.urls.__enter__()

        def side_effect():
            # TODO: there is no nice way to get the request in a side_effect
            # callback.
            request = collect._resps[-1][-1]
            self.add_log_entry(request)

        collect = self.urls.register(
            method='POST',
            path='/build-worker/user_name/queue_name/worker_id/jobs/123/tagged-log',
            content={'terminated':False},
            side_effect=side_effect)

    def tearDown(self):
        self.urls.__exit__()
        self.urls = None
        os.unlink(self.filepath)

    def mk_log(self, **kwargs):
        return BuildLog(
            BinstarBuildAPI(),
            "user_name",
            "queue_name",
            "worker_id",
            123,
            filename=self.filepath,
            **kwargs)

    def assertContentEqual(self, expected):
        with open(self.filepath, 'rb') as fd:
            local_log = fd.read()
        server_log = b''.join(log['msg'] for log in self.log_entries)

        self.assertMultiLineEqual(expected, local_log)
        self.assertMultiLineEqual(expected, server_log)

    def test_write(self):
        with self.mk_log() as log:
            self.assertTrue(log.writable())
            res = log.write(b'test')
            self.assertEqual(4, res)

            with self.assertRaises(TypeError):
                log.write('this is unicode')

        self.assertContentEqual(b'test')

    def test_write_invalid_unicode(self):
        with self.mk_log() as log:
            log.write(b'this can not be unicode \xe2')

        self.assertContentEqual(b'this can not be unicode \xe2')

    def test_read(self):
        with self.mk_log() as log:
            self.assertFalse(log.readable())

    def test_context(self):
        log = self.mk_log()
        self.assertFalse(log.fd.closed)
        with log:
            self.assertFalse(log.fd.closed)
        self.assertTrue(log.fd.closed)

    def test_invalid_metadata_preserved(self):
        with self.mk_log() as log:
            log.write(build_log.METADATA_PREFIX + b'abcd')

        self.assertEqual(log.metadata, {'section': 'dequeue_build'})
        self.assertContentEqual(build_log.METADATA_PREFIX + b'abcd')

    def test_metadata_stripped(self):
        # The metadata should not be included in the file output or sent to
        # the server.

        with self.mk_log() as log:
            log.write(build_log.encode_metadata({'section': 'my_section', 'command': 'echo "oops"'}))
            log.write(b'echo "oops"\n')
            log.write(b'oops\n')
            log.write(build_log.encode_metadata({'section': 'section_2', 'command': 'echo "nope"'}))
            log.write(b'echo "nope"\n')
            log.write(b'nope\n')

        self.assertContentEqual(
            '''\
echo "oops"
oops
echo "nope"
nope
''')



if __name__ == '__main__':
    unittest.main()
