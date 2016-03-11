from glob import glob
import os
import unittest

from binstar_client import errors
from binstar_build_client.worker.register import WorkerConfiguration


test_workers = os.path.abspath('./test-workers')

class Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        WorkerConfiguration.REGISTERED_WORKERS_DIR = test_workers
        if not os.path.exists(test_workers):
            os.mkdir(test_workers)
        super(Test, cls).setUpClass()

    def tearDown(self):

        for fn in glob(os.path.join(test_workers, '*')):
            os.unlink(fn)

        unittest.TestCase.tearDown(self)


    def test_str(self):

        wc = WorkerConfiguration(
            'worker_name',
            'worker_id', 'username', 'queue',
            'platform', 'hostname', 'dist'
        )

        expected = """WorkerConfiguration
\tpid: None
\tdist: dist
\thostname: hostname
\tname: worker_name
\tplatform: platform
\tqueue: queue
\tusername: username
\tworker_id: worker_id
"""
        self.assertEqual(str(wc), expected)


    def test_running(self):

        wc = WorkerConfiguration(
             'worker_name',
             'worker_id', 'username', 'queue',
             'platform', 'hostname', 'dist'
        )

        self.assertFalse(wc.is_running())

        with wc.running():
            self.assertIsNotNone(wc.pid)
            self.assertTrue(wc.is_running())

        self.assertFalse(wc.is_running())

    def test_already_running(self):

        wc = WorkerConfiguration(
            'worker_name',
            'worker_id', 'username', 'queue',
            'platform', 'hostname', 'dist'
        )

        self.assertFalse(wc.is_running())

        with wc.running():

            with self.assertRaises(errors.BinstarError):

                with wc.running():
                    pass

            self.assertTrue(wc.is_running())

        self.assertFalse(wc.is_running())

if __name__ == '__main__':
    unittest.main()
