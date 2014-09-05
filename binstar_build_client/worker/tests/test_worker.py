import unittest
from binstar_build_client.worker.worker import Worker
from mock import Mock
import os

class Test(unittest.TestCase):

    def test_worker_context(self):
        bs = Mock()
        bs.register_worker.return_value = 'test_worker_id'
        args = Mock()
        args.cwd = '.'

        worker = Worker(bs, args)
        worker.STATE_FILE = 'worker_test_state.yaml'

        with worker.worker_context() as worker_id:
            self.assertEqual(worker_id, 'test_worker_id')
            self.assertTrue(os.path.isfile(worker.STATE_FILE))

        self.assertEqual(bs.remove_worker.call_count, 1)
        self.assertFalse(os.path.isfile(worker.STATE_FILE))

    @unittest.skip('Not Implemented')
    def _handle_job(self):
        pass

    @unittest.skip('Not Implemented')
    def test_download_build_source(self):
        pass

    @unittest.skip('Not Implemented')
    def test_build(self):
        pass

    @unittest.skip('Not Implemented')
    def test_job_loop(self):
        pass


if __name__ == '__main__':
    unittest.main()
