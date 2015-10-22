from __future__ import print_function, unicode_literals, absolute_import

import unittest
from mock import Mock, patch

from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker_commands.register import get_platform
import os
import stat
from binstar_build_client.worker.utils import script_generator

try_unlink = lambda path: os.unlink(path) if os.path.isfile(path) else None

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


class MyWorker(Worker):
    download_build_source = Mock()
    download_build_source.return_value = 'build_source_filename'

    def __init__(self):
        self.SLEEP_TIME = 0
        bs = Mock()
        bs.log_build_output.return_value = False
        args = Mock()
        args.status_file = None
        args.timeout = 100
        args.show_new_procs = False

        worker_config = WorkerConfiguration(
            'worker_id', 'username', 'queue', 'test_platform', 'test_hostname', 'dist')

        Worker.__init__(self, bs, worker_config, args)

    def working_dir(self, *args):
        return os.path.abspath('test_worker')


class Test(unittest.TestCase):

    def write_sript(self, mock_gen_build_script, exit_code, wait=None):

        mock_gen_build_script.return_value = script_path = os.path.abspath('script_filename.bash')
        self.addCleanup(try_unlink, script_path)

        with open(script_path, 'w') as fd:
            print('#!/bin/bash', file=fd)
            print('echo hello', file=fd)

            if wait:
                print('echo sleep for {} seconds'.format(wait), file=fd)
                print('sleep {}'.format(wait), file=fd)

            print('echo exit {}'.format(exit_code), file=fd)
            print('exit {}'.format(exit_code), file=fd)

        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)

    @patch('binstar_build_client.worker.utils.process_wrappers.BuildProcess')
    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build(self, gen_build_script, mock_BuildProcess):

        def mock_readline(l=[]):
            l.append(None)
            if len(l) >= 3:
                return ''

            return 'ping'

        mock_BuildProcess().wait.return_value = 0
        mock_BuildProcess().poll.return_value = 0
        mock_BuildProcess().readline = mock_readline

        gen_build_script.return_value = 'script_filename'

        worker = MyWorker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)
        self.assertFalse(failed)
        self.assertEqual(status, 'success')

        popen_args = mock_BuildProcess.call_args[0][0]
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

    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_success(self, gen_build_script):

        self.write_sript(gen_build_script, script_generator.EXIT_CODE_OK)
        worker = MyWorker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertFalse(failed)
        self.assertEqual(status, 'success')

        expected_output = ("Building on worker test_hostname (platform test_platform)\n"
            "Starting build job_name\n"
            "hello\n"
            "exit 0\n")

        with open(worker.build_logfile(job_data)) as fd:
            output = fd.read()
            self.assertMultiLineEqual(output, expected_output)


    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_fail(self, gen_build_script):

        self.write_sript(gen_build_script, script_generator.EXIT_CODE_FAILED)

        worker = MyWorker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'failure')

    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_error(self, gen_build_script):


        self.write_sript(gen_build_script, script_generator.EXIT_CODE_ERROR)

        worker = MyWorker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'error')


    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_timeout(self, gen_build_script):

        self.write_sript(gen_build_script, script_generator.EXIT_CODE_OK, wait=2)

        worker = MyWorker()
        worker.args.timeout = 0.5

        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'error')

        expected_output = ("Building on worker test_hostname (platform test_platform)\n"
            "Starting build job_name\n"
            "hello\n"
            "sleep for 2 seconds\n\n"
            "Timeout: build exceeded maximum build time of 0.5 seconds\n"
            "[Terminated]\n"
        )

        with open(worker.build_logfile(job_data)) as fd:
            output = fd.read()
            self.assertMultiLineEqual(output, expected_output)

    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_iotimeout(self, gen_build_script):

        self.write_sript(gen_build_script, script_generator.EXIT_CODE_OK, wait=2)

        worker = MyWorker()
#         worker.args.timeout = 0.5

        job_data = default_build_data()
        job_data['build_item_info']['instructions']['iotimeout'] = 0.5
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'error')

        expected_output = ("Building on worker test_hostname (platform test_platform)\n"
            "Starting build job_name\n"
            "hello\n"
            "sleep for 2 seconds\n\n\n"
            "Timeout: No output from program for 0.5 seconds\n\n"
            "Timeout: If you require a longer timeout you may set the 'iotimeout' "
              "variable in your .binstar.yml file\n"
            "[Terminated]\n"
        )

        with open(worker.build_logfile(job_data)) as fd:
            output = fd.read()
            self.assertMultiLineEqual(output, expected_output)



if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
