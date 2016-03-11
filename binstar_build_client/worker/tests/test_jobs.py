from __future__ import print_function, unicode_literals, absolute_import

import copy
import datetime
import unittest

from io import BytesIO
from mock import Mock, patch
import os
import shutil
import stat
import requests

from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker_commands.register import get_platform
from binstar_build_client.worker.utils import script_generator
from binstar_build_client.worker.utils.build_log import BuildLog
from binstar_build_client.worker.docker_worker import DockerWorker
import warnings
import tempfile
import shutil


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
def data_path(filename):
    return os.path.join(DATA_DIR, filename)

try_unlink = lambda path: os.unlink(path) if os.path.isfile(path) else None

started_date = datetime.datetime.utcnow().isoformat()
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
                "after_error": "echo UNIQUE AFTER ERROR MARKER",
                'install_channels': ['r', 'python', 'other_channel']
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
        "job_name": "job_name",
        "BUILD_UTC_DATETIME": started_date,
    }


class MyWorker(Worker):
    download_build_source = Mock()
    download_build_source.return_value = data_path('example_package.tar.gz')

    def __init__(self):
        self.SLEEP_TIME = 0
        bs = Mock()
        bs.log_build_output.return_value = False
        bs.log_build_output_structured.return_value = False
        args = Mock()
        args.status_file = None
        args.timeout = 100
        args.show_new_procs = False
        args.cwd = tempfile.mkdtemp()

        worker_config = WorkerConfiguration(
            'worker_name',
            'worker_id', 'username', 'queue',
            'test_platform', 'test_hostname', 'dist'
        )

        super(MyWorker, self).__init__(bs, worker_config, args)


class Test(unittest.TestCase):
    if os.name == 'nt':

        def write_script(self, mock_gen_build_script, exit_code, wait=None):
            tempdir = tempfile.gettempdir()

            mock_gen_build_script.return_value = script_path = os.path.join(tempdir, 'script_filename.bat')
            self.addCleanup(try_unlink, script_path)

            with open(script_path, 'w') as fd:
                print('@echo off', file=fd)
                print('echo hello', file=fd)

                if wait:
                    print('echo sleep for {} seconds'.format(wait), file=fd)
                    print('sleep {}'.format(wait), file=fd)

                print('echo exit {}'.format(exit_code), file=fd)
                print('EXIT /B {}'.format(exit_code), file=fd)

    else:
        def write_script(self, mock_gen_build_script, exit_code, wait=None):
            tempdir = tempfile.gettempdir()

            mock_gen_build_script.return_value = script_path = os.path.join(tempdir, 'script_filename.sh')
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

    def get_worker(self):
        worker = MyWorker()
        return worker

    @patch('binstar_build_client.worker.utils.process_wrappers.BuildProcess')
    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build(self, gen_build_script, mock_BuildProcess):

        def mock_readline(l=[]):
            l.append(None)
            if len(l) >= 3:
                return b''

            return b'ping'

        stdout = BytesIO()

        mock_BuildProcess().wait.return_value = 0
        mock_BuildProcess().poll.return_value = 0
        mock_BuildProcess().stdout = stdout

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
            data_path('example_package.tar.gz'),
        ]
        ending_posix = popen_args[0].split('/')[-1]
        ending_win = popen_args[0].split('\\')[-1]
        self.assertIn('script_filename', (ending_win, ending_posix))
        self.assertEqual(popen_args[1:], expected_args[1:])

    expected_output_success = (
        "Building on worker test_hostname (platform test_platform)\n"
        "Starting build job_name at {0}\n"
        "hello\n"
        "exit 0\n"
    ).format(started_date)

    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_success(self, gen_build_script):

        self.write_script(gen_build_script, script_generator.EXIT_CODE_OK)

        worker = self.get_worker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertFalse(failed)
        self.assertEqual(status, 'success')


        with open(worker.build_logfile(job_data)) as fd:
            output = fd.read()
            self.assertMultiLineEqual(output, self.expected_output_success)


    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_fail(self, gen_build_script):

        self.write_script(gen_build_script, script_generator.EXIT_CODE_FAILED)

        worker = self.get_worker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'failure')

    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_error(self, gen_build_script):


        self.write_script(gen_build_script, script_generator.EXIT_CODE_ERROR)

        worker = self.get_worker()
        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'error')


    expected_output_timeout = (
        "Building on worker test_hostname (platform test_platform)\n"
        "Starting build job_name at {0}\n"
        "hello\n"
        "sleep for 2 seconds\n\n"
        "Timeout: build exceeded maximum build time of 0.5 seconds\n"
        "[Terminated]\n"
    ).format(started_date)


    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_timeout(self, gen_build_script):

        self.write_script(gen_build_script, script_generator.EXIT_CODE_OK, wait=2)

        worker = self.get_worker()
        worker.args.timeout = 0.5

        job_data = default_build_data()
        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'error')


        with open(worker.build_logfile(job_data)) as fd:
            output = fd.read()
            self.assertMultiLineEqual(output, self.expected_output_timeout)

    expected_output_iotimeout = (
        "Building on worker test_hostname (platform test_platform)\n"
        "Starting build job_name at {0}\n"
        "hello\n"
        "sleep for 2 seconds\n\n"
        "Timeout: No output from program for 0.5 seconds\n"
        "\tIf you require a longer timeout you may set the 'iotimeout' "
          "variable in your .binstar.yml file\n"
        "[Terminated]\n"
    ).format(started_date)

    @patch('binstar_build_client.worker.utils.script_generator.gen_build_script')
    def test_build_iotimeout(self, gen_build_script):

        self.write_script(gen_build_script, script_generator.EXIT_CODE_OK, wait=2)

        worker = self.get_worker()
#         worker.args.timeout = 0.5

        job_data = default_build_data()
        job_data['build_item_info']['instructions']['iotimeout'] = 0.5

        failed, status = worker.build(job_data)

        self.assertTrue(failed)
        self.assertEqual(status, 'error')

        with open(worker.build_logfile(job_data)) as fd:
            output = fd.read()
            self.assertMultiLineEqual(output, self.expected_output_iotimeout)


    def test_auto_env_variables(self):

        build_data = copy.deepcopy(default_build_data())
        build_data['build_item_info']['engine'] = 'python=2.7 numpy=1.9 other_req=10'
        exports = script_generator.create_exports(build_data, '.')
        self.assertEqual("19", exports['CONDA_NPY'])

    def test_working_dir(self):
        build_data = copy.deepcopy(default_build_data())
        exports = script_generator.create_exports(build_data, '/some/dir')
        self.assertEqual(exports['WORKING_DIR'], '/some/dir')

    def test_install_channels(self):
        working_dir = tempfile.mkdtemp()
        try:
            script = script_generator.gen_build_script(working_dir,
                                                       working_dir,
                                                       default_build_data())
            with open(script, 'r') as f:
                contents = f.read()
            self.assertIn('--add channels r', contents)
            self.assertIn('--add channels python', contents)
            self.assertIn('--add channels other_channel', contents)

        finally:
            shutil.rmtree(working_dir)

    def test_auto_install_channels(self):
        working_dir = tempfile.mkdtemp()
        try:
            build_data = default_build_data()
            build_data['build_item_info']['instructions']['install_channels'] = []
            build_data['build_item_info']['engine'] = 'r'
            script = script_generator.gen_build_script(working_dir,
                                                       working_dir,
                                                       build_data)
            with open(script, 'r') as f:
                contents = f.read()
            self.assertIn('--add channels r', contents)

        finally:
            shutil.rmtree(working_dir)



def have_docker():
    if os.environ.get('NO_DOCKER_TESTS'):
        return False

    try:
        import docker
        from docker.utils import kwargs_from_env
    except:
        warnings.warn("Skip Docker Tests: dockerpy is not installed")
        return False

    client = docker.Client(
        version=os.environ.get('DOCKER_VERSION'),
        **kwargs_from_env(assert_hostname=False)
    )

    try:
        images = client.images('binstar/linux-64')
    except docker.errors.NotFound as err:
        warnings.warn("Skip Docker Tests: {}".format(err))
        return False
    except requests.ConnectionError:
        warnings.warn("Skip Docker Tests: image binstar/linux-64 is not pulled")
        return False

    return True

class TestDockerWorker(DockerWorker):
    download_build_source = Mock()
    download_build_source.return_value = data_path('example_package.tar.gz')

    def __init__(self):
        self.SLEEP_TIME = 0
        bs = Mock()
        bs.log_build_output_structured.return_value = False
        bs.log_build_output.return_value = False

        args = Mock()
        args.status_file = None
        args.timeout = 100
        args.show_new_procs = False
        args.image = 'binstar/linux-64'
        args.cwd = tempfile.mkdtemp()

        worker_config = WorkerConfiguration(
            'worker_id', 'worker_id', 'username', 'queue', 'test_platform',
            'test_hostname', 'dist')

        super(TestDockerWorker, self).__init__(bs, worker_config, args)



@unittest.skipIf(not have_docker(), "Don't have docker")
class DockerTest(Test):
    def get_worker(self):
        worker = TestDockerWorker()
        return worker

    expected_output_success = (
        "Building on worker test_hostname (platform test_platform)\n"
        "Starting build job_name at {0}\n"
        "Docker Image: binstar/linux-64\n"
        "Docker: Create container\n"
        "Docker: Attach output\n"
        "Docker: Start\n"
        "hello\n"
        "exit 0\n"
    ).format(started_date)

    expected_output_timeout = (
        "Building on worker test_hostname (platform test_platform)\n"
        "Starting build job_name at {0}\n"
        "Docker Image: binstar/linux-64\n"
        "Docker: Create container\n"
        "Docker: Attach output\n"
        "Docker: Start\n"
        "hello\n"
        "sleep for 2 seconds\n\n"
        "Timeout: build exceeded maximum build time of 0.5 seconds\n"
        "[Terminated]\n"
    ).format(started_date)

    expected_output_iotimeout = (
        "Building on worker test_hostname (platform test_platform)\n"
        "Starting build job_name at {0}\n"
        "Docker Image: binstar/linux-64\n"
        "Docker: Create container\n"
        "Docker: Attach output\n"
        "Docker: Start\n"
        "hello\n"
        "sleep for 2 seconds\n\n"
        "Timeout: No output from program for 0.5 seconds\n"
        "\tIf you require a longer timeout you may set the 'iotimeout' "
          "variable in your .binstar.yml file\n"
        "[Terminated]\n"
    ).format(started_date)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
