'''
Created on Feb 6, 2014

@author: sean
'''
import unittest
from binstar_build_client.worker.utils.buffered_io import BufferedPopen
import io


class Test(unittest.TestCase):


    def test_stdout(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['echo', 'hello'], stdout=stdout)
        self.assertEqual(p0.wait(), 0)
        self.assertEqual(stdout.getvalue(), 'hello\n')

    def test_stdout_error(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo hello; bad-command'], stdout=stdout)
        self.assertNotEqual(p0.wait(), 0)
        self.assertTrue(stdout.getvalue().startswith('hello\n'))

    def test_stderr(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo stdout 2>&1; echo stderr 1>&2;'], stdout=stdout)
        self.assertEqual(p0.wait(), 0)
        self.assertEqual(stdout.getvalue(), 'stdout\nstderr\n')

    def test_timeout(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo hello && sleep 100 && echo goodby'], stdout=stdout, iotimeout=1)
        self.assertNotEqual(p0.wait(), 0)
        self.assertIn('hello', stdout.getvalue())
        self.assertIn('Timeout: No output from program for 1 seconds', stdout.getvalue())
        self.assertFalse(p0._io_thread.isAlive())

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_timeout']
    unittest.main()
