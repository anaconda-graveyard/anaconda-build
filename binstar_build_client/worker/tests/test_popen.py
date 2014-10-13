import unittest
from binstar_build_client.worker.utils.buffered_io import BufferedPopen
import io
import os
skipWindows = unittest.skipIf(os.name == 'nt', 'This test does not run on windows')
skipPosix = unittest.skipIf(os.name != 'nt', 'This test does not run on Posix')

class Test(unittest.TestCase):


    def test_stdout(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['echo', 'hello'], stdout=stdout)
        self.assertEqual(p0.wait(), 0)
        self.assertEqual(stdout.getvalue().strip(), 'hello')

    @skipWindows
    def test_stdout_error(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo hello; bad-command'], stdout=stdout)
        return_code = p0.wait()
        self.assertNotEqual(return_code, 0)
        self.assertTrue(stdout.getvalue().startswith('hello\n'))

    @skipPosix
    def test_stdout_error_win(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['cmd', '/c', 'echo hello & bad-command'], stdout=stdout)
        return_code = p0.wait()
        self.assertNotEqual(return_code, 0)

        self.assertTrue(stdout.getvalue().startswith('hello'))

    @skipWindows
    def test_stderr(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo stdout 2>&1; echo stderr 1>&2;'], stdout=stdout)
        self.assertEqual(p0.wait(), 0)
        self.assertEqual(stdout.getvalue(), 'stdout\nstderr\n')

    @skipWindows
    def test_iotimeout(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['bash', '-c', 'echo hello && sleep 100 && echo goodby'], stdout=stdout, iotimeout=1)
        self.assertNotEqual(p0.wait(), 0)
        self.assertIn('hello', stdout.getvalue())
        self.assertIn('Timeout: No output from program for 1 seconds', stdout.getvalue())
        self.assertFalse(p0._iostream.isAlive())


    @skipPosix
    def test_iotimeout_win(self):
        stdout = io.BytesIO()
        p0 = BufferedPopen(['cmd', '/c', 'echo hello && sleep 100 && echo goodby'], stdout=stdout, iotimeout=1)
        returncode = p0.wait()
        print("returncode", returncode)
        # self.assertNotEqual(returncode, 0)
        self.assertIn('hello', stdout.getvalue())
        self.assertIn('Timeout: No output from program for 1 seconds', stdout.getvalue())
        self.assertFalse(p0._io_thread.isAlive())


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_timeout']
    unittest.main()
