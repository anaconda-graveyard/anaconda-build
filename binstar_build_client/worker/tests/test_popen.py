'''
Created on Feb 6, 2014

@author: sean
'''
import unittest
from binstar_build_client.worker.utils.buffered_io import BufferedPopen
import io


class Test(unittest.TestCase):

    def test_simple(self):
        p0 = BufferedPopen(['echo', 'hello'])
        self.assertEqual(p0.wait(), 0)

    def test_stdout(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['echo', 'hello'], stdout=stdout)
        self.assertEqual(p0.wait(), 0)
        self.assertEqual(stdout.getvalue(), 'hello\n')

    def test_stderr(self):
        stderr = io.BytesIO()
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo stdout 2>&1; echo stderr 1>&2;'], stderr=stderr, stdout=stdout)
        self.assertEqual(p0.wait(), 0)
        self.assertEqual(stderr.getvalue(), 'stderr\n')
        self.assertEqual(stdout.getvalue(), 'stdout\n')

    def test_timout(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo hello && sleep 10 && echo goodby'], stdout=stdout, iotimeout=1)
        self.assertNotEqual(p0.wait(), 0)
        self.assertIn('hello', stdout.getvalue())
        self.assertIn('Timeout: No output from program for 1 seconds', stdout.getvalue())
        self.assertFalse(p0._thread.isAlive())

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_timeout']
    unittest.main()
