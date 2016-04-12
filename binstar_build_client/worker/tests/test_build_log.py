from __future__ import print_function, unicode_literals, absolute_import

import os
import tempfile
import unittest

import time

import array
from binstar_client.tests import urlmock
import mock
from six import text_type
from six.moves import urllib

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.utils import build_log
from binstar_build_client.worker.utils.build_log import BuildLog, wrap_file
from binstar_build_client.worker.utils.generator_file import GeneratorFile

def mk_log(**kwargs):
    return BuildLog(
        BinstarBuildAPI(),
        "user_name",
        "queue_name",
        "worker_id",
        123,
        **kwargs)


class TestBuildLog(unittest.TestCase):

    def add_log_entry(self, request):
        # werkzeug decodes form content with errors=replace, but urllib.parse.parse_qsl
        # returns `str` in Python 2. We should decode for consistent behavior.
        log = {
           key: value if isinstance(value, text_type) else value.decode('utf-8', 'replace')
           for key, value in urllib.parse.parse_qsl(request.body)
        }
        self.log_entries.append(log)

    def setUp(self):
        tempdir = tempfile.gettempdir()
        self.filepath = os.path.join(tempdir, 'build-log-test.txt')
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
        try:
            os.unlink(self.filepath)
        except (OSError, IOError):
            pass

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
        server_log = b''.join(log['msg'].encode('utf-8') for log in self.log_entries)

        self.assertEqual(expected, local_log)
        self.assertEqual(expected, server_log)

    def test_write(self):
        with self.mk_log() as log:
            self.assertTrue(log.writable())
            res = log.writeline(b'test\n')
            self.assertEqual(5, res)

            with self.assertRaises(TypeError):
                log.writeline('this is unicode')

        self.assertContentEqual(b'test\n')

    def test_write_invalid_unicode(self):
        with self.mk_log() as log:
            log.writeline(b'this can not be unicode \xe2\n')

        with open(self.filepath, 'rb') as fd:
            local_log = fd.read()
        server_log = b''.join(log['msg'].encode('utf-8') for log in self.log_entries)

        self.assertEqual(local_log, b'this can not be unicode \xe2\n')
        # the server replaces the bad byte with a unicode replacement character
        # (when performing form decoding)
        self.assertEqual(server_log, 'this can not be unicode \ufffd\n'.encode('utf-8'))

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
            log.writeline(build_log.METADATA_PREFIX + b'abcd')

        self.assertEqual(log.metadata, {'section': 'dequeue_build'})
        self.assertContentEqual(build_log.METADATA_PREFIX + b'abcd')

    def test_metadata_stripped(self):
        # The metadata should not be included in the file output or sent to
        # the server.

        with self.mk_log() as log:
            log.writeline(build_log.encode_metadata({'section': 'oops', 'command': 'echo "oops"'}))
            log.writeline(b'echo "oops"\n')
            log.writeline(b'oops\n')
            log.writeline(build_log.encode_metadata({'section': 'nope', 'command': 'echo "nope"'}))
            log.writeline(b'echo "nope"\n')
            log.writeline(b'nope\n')

        self.assertContentEqual(
            b'''\
echo "oops"
oops
echo "nope"
nope
''')

        for entry in self.log_entries:
            self.assertIn(entry['section'], entry['msg'])


    def test_loud_shows_cr(self):
        with self.mk_log() as log:
            log.writeline(b'this is some normal data\n')
            log.writeline(b'this is data that is overwriting\r')
            log.writeline(b'this is more normal data\n')

        self.assertContentEqual(
            b'this is some normal data\n'
            b'this is data that is overwriting\r'
            b'this is more normal data\n'
        )

    def test_quiet_hides_cr(self):
        with self.mk_log(quiet=True) as log:
            log.writeline(b'this is some normal data\n')
            log.writeline(b'this is data that is overwriting\r')
            log.writeline(b'this is more normal data\n')

        self.assertContentEqual(
            b'this is some normal data\n'
            b'this is more normal data\n'
        )

    def test_quiet_shows_crlf(self):
        with self.mk_log(quiet=True) as log:
            log.writeline(b'this is some normal data\n')
            log.writeline(b'this is some normal data with crlf\r\n')
            log.writeline(b'this is more normal data\n')

        self.assertContentEqual(
            b'this is some normal data\n'
            b'this is some normal data with crlf\r\n'
            b'this is more normal data\n'
        )


class TestServer(unittest.TestCase):
    def setUp(self):
        tempdir = tempfile.mkdtemp()
        self.filepath = os.path.join(tempdir, 'build-log-output.txt')

    def tearDown(self):
        try:
            os.unlink(self.filepath)
        except (OSError, IOError):
            pass

    @urlmock.urlpatch
    def test_falls_back(self, urls):
        urls.register(
            method='POST',
            path='/build-worker/user_name/queue_name/worker_id/jobs/123/tagged-log',
            status=404,
            )
        urls.register(
            method='POST',
            path='/build-worker/user_name/queue_name/worker_id/jobs/123/log',
            status=200,
        )

        with mk_log(filename=self.filepath) as log:
            log.writeline(b'This is some data\n')

        urls.assertAllCalled()

    @urlmock.urlpatch
    def test_after_success_does_not_fall_back(self, urls):
        log_tagged = urls.register(
            method='POST',
            path='/build-worker/user_name/queue_name/worker_id/jobs/123/tagged-log',
            status=200,
        )
        log_simple = urls.register(
            method='POST',
            path='/build-worker/user_name/queue_name/worker_id/jobs/123/log',
            status=200,
        )

        with mk_log(filename=self.filepath) as log:
            log.writeline(b'This is some data\n')
            log.flush()

            self.assertEqual(len(log_tagged._resps), 1)
            self.assertEqual(len(log_simple._resps), 0)

            log_tagged = urls.register(
                method='POST',
                path='/build-worker/user_name/queue_name/worker_id/jobs/123/tagged-log',
                status=404,
            )

            log.writeline(b'This is some later data\n')
            log.flush()

            self.assertEqual(len(log_tagged._resps), 1)
            self.assertEqual(len(log_simple._resps), 0)


    @mock.patch('binstar_build_client.worker.utils.build_log.MAX_WRITE_ATTEMPTS', 2)
    @urlmock.urlpatch
    def test_terminate_server_error(self, urls):
        log_tagged = urls.register(
            method='POST',
            path='/build-worker/user_name/queue_name/worker_id/jobs/123/tagged-log',
            status=500,
        )

        with mk_log(filename=self.filepath) as log:
            log.writeline(b'This is some data\n')
            log.flush()
            self.assertEqual(len(log_tagged._resps), 1)
            self.assertFalse(log.terminated(), "Should not terminate after the first failure")
            log.flush()
            self.assertEqual(len(log_tagged._resps), 2)
            self.assertTrue(log.terminated(), "Should terminate after MAX_WRITE_ATTEMPTS")


class TestBuffering(unittest.TestCase):

    def test_wrapper(self):
        def output():
            yield b'Content\n'
            yield b'Content\rall\rin\ra single\rrow\n'
            yield b'Content '
            yield b'In a line\n'
            yield b'Windows output\r\n'
        fd = wrap_file(GeneratorFile(output()))

        lines = fd.readlines()

        self.assertEqual([
            'Content\n',
            'Content\r',
            'all\r',
            'in\r',
            'a single\r',
            'row\n',
            'Content In a line\n',
            'Windows output\r\n',
        ], lines)

    def test_generator_file(self):
        def output():
            yield b'Some '
            yield b'output that is larger than the buffer\n'
            yield b'And more'
        fd = GeneratorFile(output())

        bufs = []
        small_buf = bytearray(8)
        n = fd.readinto(small_buf)
        while n:
            bufs.append(bytes(small_buf[:n]))
            n = fd.readinto(small_buf)

        self.assertEqual(b''.join(bufs),
                         b'Some output that is larger than the buffer\nAnd more')

    def test_generator_file_array(self):
        def output():
            yield b'Some '
            yield b'output that is larger than the buffer\n'
            yield b'And more'
        fd = GeneratorFile(output())

        bufs = []
        small_buf = array.array('b', b'\x00' * 8)
        n = fd.readinto(small_buf)
        while n:
            bufs.append(small_buf.tostring()[:n])
            n = fd.readinto(small_buf)

        self.assertEqual(b''.join(bufs),
                         b'Some output that is larger than the buffer\nAnd more')

    def test_buffer_send_when_available(self):
        def output():
            yield b'Data\r'
            time.sleep(.05)
            # The line `Data\r` cannot be sent until `More` arrives - it might be followed by `\n`
            yield b'More'
            time.sleep(.05)
            yield b' data\n'

        fd = wrap_file(GeneratorFile(output()))

        time_0 = time.time()
        line_1, time_1 = (fd.readline(), time.time())
        line_2, time_2 = (fd.readline(), time.time())

        self.assertEqual("Data\r", line_1)
        self.assertEqual("More data\n", line_2)

        elapsed_1 = time_1 - time_0
        elapsed_2 = time_2 - time_0

        # We need to wait for more
        self.assertTrue(.05 < elapsed_1 < .1, "Should wait for the line ending with CR until more data arrives")
        self.assertGreater(elapsed_2, .1, "Should wait for the second line to complete")


if __name__ == '__main__':
    unittest.main()
