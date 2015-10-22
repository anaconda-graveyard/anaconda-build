from __future__ import print_function, unicode_literals, absolute_import

import unittest
from mock import Mock, patch

from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker_commands.register import get_platform


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


class Test(unittest.TestCase):

    @patch('binstar_build_client.worker.utils.process_wrappers.BuildProcess')
    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
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

        popen_args = mock_Popen.call_args[0][0]
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


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
