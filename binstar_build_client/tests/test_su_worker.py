'''
Test worker.su_worker.SuWorker.

This test is only run if user is root, there is a root python install, and there is a
build user called 'test_build_worker'.
'''
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

from argparse import Namespace
from mock import patch
import io
import os
from glob import glob
import psutil
import subprocess as sp
import unittest

from binstar_client import errors
from binstar_client.tests.urlmock import urlpatch
from binstar_client.utils import get_binstar
import yaml

from binstar_client.tests.fixture import CLITestCase
from binstar_build_client import BinstarBuildAPI
from binstar_build_client.scripts.worker import main
from binstar_build_client.worker.utils import process_wrappers
from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.tests.test_worker_script import (worker_data,
                                                           test_workers)

import binstar_build_client.worker.su_worker as su_worker

TEST_BUILD_WORKER = 'test_build_worker'
SU_WORKER_DEFAULT_PATH = su_worker.SU_WORKER_DEFAULT_PATH

try:
    is_valid_su_worker = su_worker.validate_su_worker(TEST_BUILD_WORKER,
                                                      SU_WORKER_DEFAULT_PATH)
except errors.BinstarError:
    is_valid_su_worker = False
standard_root_install = os.path.exists(SU_WORKER_DEFAULT_PATH)


class TestSuWorker(CLITestCase):

    @classmethod
    def setUpClass(cls):
        super(TestSuWorker, cls).setUpClass()

    def tearDown(self):

        for fn in glob(os.path.join(os.path.expanduser('~root'),'.workers', '*')):
            if 'worker_id' == os.path.basename(fn):
                os.unlink(fn)

        unittest.TestCase.tearDown(self)

    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    @urlpatch
    @patch('binstar_build_client.worker.su_worker.SuWorker')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_su_worker(self, urls, load, SuWorker):
        '''Test su_worker CLI '''

        load.return_value = self.new_worker_config()
        main(['--show-traceback', 'su_run',
              'worker_id', TEST_BUILD_WORKER], False)
        self.assertEqual(SuWorker().work_forever.call_count, 1)

    def test_validate_su_worker(self):
        '''Test su_worker is only run as root, with root python install'''
        if not hasattr(os, 'getuid'):
            os.getuid = lambda: True
        with patch.object(os, 'name', return_value='posix', clear=True):
            with patch.object(os, 'getuid', return_value=0, clear=True) as getuid:
                with patch.object(os.path, 'isdir', return_value=True, clear=True) as isdir:
                    with patch.object(su_worker, 'check_conda_path', return_value=True, clear=True) as check:
                        with patch.object(su_worker, 'test_su_as_user', return_value=True, clear=True) as test_su:
                            is_valid = su_worker.validate_su_worker(TEST_BUILD_WORKER,
                                                                    SU_WORKER_DEFAULT_PATH)
                            self.assertTrue(is_valid)
                        with patch.object(su_worker, 'test_su_as_user', return_value=False, clear=True) as test_su:
                            is_valid = su_worker.validate_su_worker(TEST_BUILD_WORKER,
                                                                    SU_WORKER_DEFAULT_PATH)
                            self.assertFalse(is_valid)
        self.assertEqual(getuid.call_count, 2)
        self.assertEqual(isdir.call_count, 2)
        self.assertNotEqual(check.call_count, 0)
        self.assertEqual(test_su.call_count, 1)
        with patch.object(su_worker, 'check_conda_path', return_value=True, clear=True) as check:
            with patch.object(os.path, 'isdir', return_value=True, clear=True) as isdir:
                with patch.object(os, 'getuid', return_value=1, clear=True) as getuid:
                    with self.assertRaises(errors.BinstarError):
                        su_worker.validate_su_worker(TEST_BUILD_WORKER, SU_WORKER_DEFAULT_PATH)


    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    @unittest.skipIf(not standard_root_install,
                        'Skipping: python not at {}'.format(SU_WORKER_DEFAULT_PATH))
    def test_destroy_user_procs(self):
        '''Test if test_build_worker's processes can
        be destroyed by creating test_build_worker sleep
        subprocesses'''
        worker = self.new_su_worker()
        procs = []
        for new_proc in range(5):
            procs.append(sp.Popen(['su', '-', TEST_BUILD_WORKER, '--login',
                                   '-c', 'sleep 10000',
                                  ]))
        build_user_pids = {proc.pid for proc in procs}
        found_pids = self.find_worker_pids_parents()
        for pid in build_user_pids:
            self.assertIn(pid, found_pids)
        worker.destroy_user_procs()
        found_pids = self.find_worker_pids_parents()
        for pid in build_user_pids:
            self.assertNotIn(pid, found_pids)

    def find_worker_pids_parents(self):
        '''This finds the TEST_BUILD_WORKER's subprocesses,
        but returns the parent of the TEST_BUILD_WORKER's
        subprocesses.'''
        found_pids = []
        for proc in psutil.process_iter():
            for child in proc.children():
                try:
                    if hasattr(child, 'username') and callable(child.username):
                        is_worker_proc = child.username() == TEST_BUILD_WORKER
                    else:
                        is_worker_proc = child.uids().real != 0
                    if is_worker_proc:
                        found_pids.append(proc.pid)
                except psutil.AccessDenied:
                    pass
        return found_pids

    @patch('binstar_build_client.worker.utils.process_wrappers.SuBuildProcess')
    @patch('binstar_build_client.worker.su_worker.SuWorker.destroy_user_procs')
    @patch('binstar_build_client.worker.su_worker.SuWorker.clean_home_dir')
    @patch('binstar_build_client.worker.su_worker.validate_su_worker')
    @patch('binstar_build_client.worker.worker.Worker._finish_job')
    @patch('subprocess.check_output')
    @unittest.skipIf(not is_valid_su_worker, "Must be valid _su_worker")
    def test_run(self, check_output, finish, validate, clean, destroy, su_build):
        self.new_worker_config()

        ok = ['echo','su_worker_test_ok']
        check_output.return_value = 'su_worker_test_ok'
        su_build.return_value = process_wrappers.BuildProcess(ok, '.')
        destroy.return_value = True
        clean.return_value = True
        validate.return_value = True
        finish.return_value = True
        worker = self.new_su_worker()
        build_data = {
            'owner':{'login': '.',},
            'package':{'name':'.',},
            'job': {'_id': '_id',},
        }
        build_log = io.BytesIO()
        timeout = iotimeout = 200
        script_filename = 'script'
        exit_code = worker.run(build_data, script_filename,
                                  build_log, timeout, iotimeout,
                                  api_token='api_token',
                                  git_oauth_token='git_oauth_token',
                                  build_filename=None, instructions=None)
        worker._finish_job(build_data, False, 'ok')
        build_log = build_log.getvalue()
        self.assertIn('su_worker_test_ok', build_log.decode())
        self.assertEqual(exit_code, 0)
        self.assertEqual(su_build.call_count, 1)
        self.assertEqual(destroy.call_count, 1)
        self.assertEqual(validate.call_count, 1)
        self.assertEqual(clean.call_count, 2)
        self.assertEqual(finish.call_count, 1)
        self.assertEqual(check_output.call_count, 1)

    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    @unittest.skipIf(not standard_root_install,
                        'Skipping: python not at {}'.format(SU_WORKER_DEFAULT_PATH))
    def test_clean_home_dir(self):
        worker = self.new_su_worker()
        home_dir = os.path.expanduser('~{}'.format(TEST_BUILD_WORKER))
        to_be_removed = os.path.join(home_dir, 'to_be_removed')
        with open(to_be_removed, 'w') as f:
            f.write('to_be_removed')
        worker.clean_home_dir()
        sorted_home_dir = sorted(os.listdir(home_dir))
        sorted_etc_worker = sorted(os.listdir('/etc/worker-skel'))
        self.assertEqual(sorted_etc_worker, sorted_home_dir)

    def test_start_when_already_running(self):
        worker_id_pid = 'test_build_worker.1234'
        if not os.path.exists(WorkerConfiguration.REGISTERED_WORKERS_DIR):
            os.mkdir(WorkerConfiguration.REGISTERED_WORKERS_DIR)
        worker_file = os.path.join(WorkerConfiguration.REGISTERED_WORKERS_DIR,
                                   worker_id_pid)
        try:
            with open(worker_file, 'w') as f:
                f.write('test_build_worker running')
            with self.assertRaises(errors.BinstarError):
                su_worker.is_build_user_running('test_build_worker')
        finally:
            if os.path.exists(worker_file):
                os.unlink(worker_file)

    def new_su_worker(self):
        args = Namespace()
        args.site = 'http://api.anaconda.org'
        args.token = None
        args.worker_id = 'worker_id'
        args.build_user = TEST_BUILD_WORKER
        args.push_back = True
        args.python_install_dir = SU_WORKER_DEFAULT_PATH
        args.cwd = '.'
        bs = get_binstar(args, cls=BinstarBuildAPI)
        worker_config = self.new_worker_config()
        return su_worker.SuWorker(bs, worker_config, args)

    def new_worker_config(self):
        worker_config = WorkerConfiguration('worker_id', 'worker_id', 'username', 'queue',
                                            'platform', 'hostname', 'dist')
        return worker_config

if __name__ == '__main__':
    unittest.main()
