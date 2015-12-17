import unittest
from binstar_build_client.worker.utils.process_wrappers import BuildProcess, WIN_32
import sys
import os
import time
import psutil
import signal

module_dir = os.path.dirname(__file__)

run_sub_process = os.path.join(module_dir, 'run_sub_process.py')
echo_hello = os.path.join(module_dir, 'echo_hello.py')

class Test(unittest.TestCase):

    def test_build_process_can_create_processes(self):

        p0 = BuildProcess([sys.executable, echo_hello], '.')
        p0.wait()

        self.assertEqual(p0.readline().strip(), 'hello')
        self.assertEqual(p0.readline().strip(), '')

    def test_terminate_process_group_naive(self):


        p0 = BuildProcess([sys.executable, run_sub_process], '.')
        time.sleep(.1)

        parent = psutil.Process(p0.pid)
        children = parent.children()

        os.kill(p0.pid, signal.SIGTERM)

        p0.wait()

        self.assertFalse(parent.is_running())
        self.assertEqual([c.is_running() for c in children], [True])

        for c in children:
            if c.is_running(): c.kill()

    @unittest.skipIf(WIN_32, 'This test should only run on posix')
    def test_terminate_process_group(self):


        p0 = BuildProcess([sys.executable, run_sub_process], '.')
        time.sleep(.1)

        parent = psutil.Process(p0.pid)
        children = parent.children()

        parent_pgid = os.getpgid(parent.pid)
        for child in children:
            self.assertEqual(parent_pgid, os.getpgid(child.pid))

        p0.kill_pg()
        p0.wait()
        self.assertFalse(parent.is_running())
        self.assertEqual([c.is_running() for c in children], [False])


    @unittest.skipIf(not WIN_32, 'This test should only run on windows')
    def test_terminate_job_object(self):

        p0 = BuildProcess([sys.executable, run_sub_process], '.')
        time.sleep(.1)

        parent = psutil.Process(p0.pid)
        children = parent.children()

        p0.kill_job()

        p0.wait()
        self.assertFalse(parent.is_running())
        self.assertEqual([c.is_running() for c in children], [False])


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_build_process_can_create_processes']
    unittest.main()

