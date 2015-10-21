from __future__ import print_function, unicode_literals, absolute_import

from mock import Mock, patch
import io
import os
import unittest

from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker_commands.register import get_platform


class MockWorker(Worker):
    def __init__(self):
        self.SLEEP_TIME = 0
        bs = Mock()
        bs.log_build_output.return_value = False
        args = Mock()
        args.status_file = None
        args.timeout = 100

        worker_config = WorkerConfiguration(
            'worker_id', 'username', 'queue', 'test_platform', 'test_hostname', 'dist')

        Worker.__init__(self, bs, worker_config, args)

def default_build_data():
    return {
        "build_item_info": {
            "engine": "python",
            "platform": get_platform(),
            "sub_build_no": 0,
            "build_no": "1.0",
            "instructions": {
                "before_script": "echo UNIQUE BEFORE SCRIPT MARKER",
                "after_failure": "echo UNIQUE AFTER FAILURE MARKER",
                "iotimeout": 61,
                "install": "echo UNIQUE INSTALL MARKER",
                "script": "echo UNIQUE SCRIPT MARKER",
                "test": "echo UNIQUE TEST MARKER",
                "after_script": "echo UNIQUE AFTER SCRIPT MARKER",
                "after_success": "echo UNIQUE AFTER SUCCESS MARKER",
                "after_error": "echo UNIQUE AFTER ERROR MARKER"
            }
        },
        "build_info": {
            "api_endpoint": "api_endpoint",
            "_id": "build_id",
            "build_no": 1
        },
        "package": {
            "name": "the_package"
        },
        "job": {
            "_id": "test_gen_build_script"
        },
        "owner": {
            "login": "me"
        },
        "upload_token": "upload_token",
        "job_name": "job_name"
    }


class Test(unittest.TestCase):
    def test_handle_job(self):

        class MyWorker(MockWorker):
            build = Mock()
            build.return_value = False, 'success'
            download_build_source = Mock()
        worker = MyWorker()
        worker.args.push_back = False
        worker._handle_job({'job':{'_id':'test_job_id'}})
        self.assertEqual(worker.build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_args[1], {'status': 'success', 'failed': False})

    def test_failed_job(self):

        class MyWorker(MockWorker):
            build = Mock()
            build.side_effect = Exception("This is an expected test error")

        worker = MyWorker()
        worker.args.push_back = False

        worker._handle_job({'job':{'_id':'test_job_id'}})

        self.assertEqual(worker.build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_args[1], {'status': 'error', 'failed': True})


    def test_download_build_source(self):

        worker = MockWorker()
        expected = b"build source"
        worker.bs.fetch_build_source.return_value = io.BytesIO(expected)

        filename = worker.download_build_source('job_id')
        self.assertTrue(os.path.isfile(filename))
        self.addCleanup(os.unlink, filename)

        with open(filename, 'rb') as fd:
            data = fd.read()
        self.assertEqual(data, expected)


    @patch('binstar_build_client.worker.utils.process_wrappers.BuildProcess')
    @patch('binstar_build_client.worker.worker.gen_build_script')
    @patch('binstar_build_client.worker.utils.timeout.kill_tree')
    def test_build(self, mock_kill_tree, gen_build_script, mock_Popen):

        def mock_readline(l=[]):
            l.append(None)
            if len(l) >= 3:
                return ''

            return 'ping'
        class MyWorker(MockWorker):
            download_build_source = Mock()
            download_build_source.return_value = 'build_source_filename'

        mock_Popen().wait.return_value = 0
        mock_Popen().poll.return_value = 0
        mock_Popen().readline = mock_readline

        gen_build_script.return_value = 'script_filename'

        worker = MyWorker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)
        self.assertFalse(failed)
        self.assertEqual(status, 'success')

        popen_args = BuildProcess.call_args[0][0]
        expected_args = [
            'script_filename',
            '--api-token',
            'upload_token',
            '--build-tarball',
            'build_source_filename'
        ]
        ending_posix = popen_args[0].split('/')[-1]
        ending_win = popen_args[0].split('\\')[-1]
        self.assertIn('script_filename', (ending_win, ending_posix))
        self.assertEqual(popen_args[1:], expected_args[1:])
        popen_kwargs = mock_Popen.call_args[1]

    def test_job_loop(self):
        worker = MockWorker()
        worker.args.one = True
        worker.bs.pop_build_job.return_value = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        jobs = list(worker.job_loop())
        self.assertEqual(len(jobs), 1)

    def test_job_loop_error(self):

        worker = MockWorker()
        worker.args.one = False
        worker.bs.pop_build_job.return_value = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}

        with self.assertRaises(TypeError):
            for job in worker.job_loop():
                raise TypeError("Expected Error")

    def test_job_context(self):

        worker = MockWorker()
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
        worker.args.one = False
        job_data = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        journal = io.StringIO()

        with worker.job_context(journal, job_data):
            raise TypeError("hai -- Expected Error")

        value = journal.getvalue()
        expected = 'starting build, test_job_id, job_name\nbuild errored, test_job_id, job_name\n'
        self.assertEqual(value, expected)

if __name__ == '__main__':
    unittest.main()
