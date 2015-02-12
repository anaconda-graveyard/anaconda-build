import io
import os
import unittest

from binstar_build_client.commands.worker import get_platform
from binstar_build_client.worker.worker import Worker
from mock import Mock, patch


class MockWorker(Worker):
    def __init__(self):
        self.SLEEP_TIME = 0
        bs = Mock()
        args = Mock()
        args.hostname = 'test_hostname'
        args.platform = 'test_platform'
        args.timeout = 100
        Worker.__init__(self, bs, args)

def default_build_data():
    return {
              'build_info':
                {'api_endpoint': 'api_endpoint',
                 'build_no': 1,
                 '_id':'build_id',
                 },
              'build_item_info':
                {'platform': get_platform(),
                 'engine': 'python',
                 'build_no': '1.0',
                 'sub_build_no': 0,
                 'instructions': {
                                  'iotimeout': 61,
                                  'install':'echo UNIQUE INSTALL MARKER',
                                  'test': 'echo UNIQUE TEST MARKER',
                                  'before_script': 'echo UNIQUE BEFORE SCRIPT MARKER',
                                  'script': 'echo UNIQUE SCRIPT MARKER',
                                  'after_failure': 'echo UNIQUE AFTER FAILURE MARKER',
                                  'after_error': 'echo UNIQUE AFTER ERROR MARKER',
                                  'after_success': 'echo UNIQUE AFTER SUCCESS MARKER',
                                  'after_script': 'echo UNIQUE AFTER SCRIPT MARKER',

                                  },
                 },
              'job':
                {'_id': 'test_gen_build_script'},
              'owner': {'login': 'me'},
              'package': {'name': 'the_package'},
              'job_name':'job_name',
              'upload_token':'upload_token'
              }

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

    def test_handle_job(self):

        class MyWorker(MockWorker):
            build = Mock()
            build.return_value = False, 'success'
            download_build_source = Mock()

        worker = MyWorker()
        worker.args.push_back = False
        worker.worker_id = 'worker_id'
        worker._handle_job({'job':{'_id':'test_job_id'}})

        self.assertEqual(worker.build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_args[1], {'status': 'success', 'failed': False})

    def test_failed_job(self):

        class MyWorker(MockWorker):
            build = Mock()
            build.side_effect = Exception

        worker = MyWorker()
        worker.args.push_back = False
        worker.worker_id = 'worker_id'

        worker._handle_job({'job':{'_id':'test_job_id'}})

        self.assertEqual(worker.build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_args[1], {'status': 'error', 'failed': True})


    def test_download_build_source(self):

        worker = MockWorker()
        worker.worker_id = 'worker_id'
        expected = "build source"
        worker.bs.fetch_build_source.return_value = io.BytesIO(expected)

        filename = worker.download_build_source('job_id')
        self.assertTrue(os.path.isfile(filename))
        self.addCleanup(os.unlink, filename)

        with open(filename) as fd:
            data = fd.read()
        self.assertEqual(data, expected)




    @patch('binstar_build_client.worker.worker.BufferedPopen')
    @patch('binstar_build_client.worker.worker.gen_build_script')
    def test_build(self, gen_build_script, BufferedPopen):
        class MyWorker(MockWorker):
            download_build_source = Mock()
            download_build_source.return_value = 'build_source_filename'

        BufferedPopen.return_value.wait.return_value = 0
        gen_build_script.return_value = 'script_filename'

        worker = MyWorker()
        worker.worker_id = 'worker_id'
        job_data = default_build_data()

        failed, status = worker.build(job_data)
        self.assertFalse(failed)
        self.assertEqual(status, 'success')

        popen_args = BufferedPopen.call_args[0][0]
        expected_args = ['script_filename', '--api-token', 'upload_token', '--build-tarball', 'build_source_filename']
        self.assertTrue(popen_args[0].endswith('/script_filename'))
        self.assertEqual(popen_args[1:], expected_args[1:])
        popen_kwargs = BufferedPopen.call_args[1]
        self.assertEqual(popen_kwargs['iotimeout'], 61)

    def test_job_loop(self):
        worker = MockWorker()
        worker.worker_id = 'worker_id'
        worker.args.one = True
        worker.bs.pop_build_job.return_value = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        jobs = list(worker.job_loop())
        self.assertEqual(len(jobs), 1)

    def test_job_loop_error(self):

        worker = MockWorker()
        worker.worker_id = 'worker_id'
        worker.args.one = False
        worker.bs.pop_build_job.return_value = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}

        with self.assertRaises(TypeError):
            for job in worker.job_loop():
                raise TypeError()

    def test_job_context(self):

        worker = MockWorker()
        worker.worker_id = 'worker_id'
        worker.args.one = False
        job_data = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        journal = io.StringIO()

        with worker.job_context(journal, job_data):
            pass

        value = journal.getvalue()
        expected = 'starting build, test_job_id, job_name\nfinished build, test_job_id, job_name\n'
        self.assertEqual(value, expected)

    def test_job_context_error(self):

        worker = MockWorker()
        worker.worker_id = 'worker_id'
        worker.args.one = False
        job_data = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        journal = io.StringIO()

        with worker.job_context(journal, job_data):
            raise TypeError("hai")

        value = journal.getvalue()
        expected = 'starting build, test_job_id, job_name\nbuild errored, test_job_id, job_name\n'
        self.assertEqual(value, expected)

if __name__ == '__main__':
    unittest.main()
