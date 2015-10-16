import unittest
from binstar_build_client.worker.register import WorkerConfiguration
import os
from glob import glob

test_workers = os.path.abspath('./test-workers')

class Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        WorkerConfiguration.REGISTERED_WORKERS_DIR = test_workers
        super(Test, cls).setUpClass()

    def tearDown(self):

        for fn in glob(os.path.join(test_workers, '*')):
            os.unlink(fn)

        unittest.TestCase.tearDown(self)


    def test_str(self):

        wc = WorkerConfiguration('worker_id', 'username', 'queue', 'platform', 'hostname', 'dist')

        expected = """<WorkerConfiguration pid=None
  dist='dist'
  hostname='hostname'
  platform='platform'
  queue='queue'
  username='username'
  worker_id='worker_id'
>
"""
        self.assertEqual(str(wc), expected)


    def test_save(self):

        wc = WorkerConfiguration('worker_id', 'username', 'queue', 'platform', 'hostname', 'dist')
        wc.save()

        self.assertFalse(wc.is_running())

        with wc.running():
            self.assertTrue(wc.is_running())

        self.assertFalse(wc.is_running())

if __name__ == '__main__':
    unittest.main()
