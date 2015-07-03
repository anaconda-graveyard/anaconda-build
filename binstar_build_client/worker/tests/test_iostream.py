from __future__ import unicode_literals, print_function
import unittest
from binstar_build_client.worker.utils.streamio import IOStream
import io


class Test(unittest.TestCase):


    def test_iostream(self):

        def line_iterator():
            yield 'line1\n'
            yield b'line2\n'
        outstream = io.StringIO()
        s = IOStream(line_iterator(), outstream)

        s.start()
        s.join()

    def test_invalid_unicode(self):

        def line_iterator():
            yield b'line1\n'
            yield b'error\x99\n'
            yield b'line3\n'
        outstream = io.StringIO()
        s = IOStream(line_iterator(), outstream)

        s.start()
        s.join()

        self.assertEqual(outstream.getvalue(), 'line1\nerror\ufffd\nline3\n')

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
