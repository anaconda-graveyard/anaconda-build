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
import psutil
import subprocess as sp 
import sys
import tempfile
import unittest

from binstar_client import errors
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_client.utils import get_binstar
from binstar_client.utils import get_config

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.scripts.build import main
import binstar_build_client.worker.su_worker as su_worker
        
TEST_BUILD_WORKER = 'test_build_worker'
SU_WORKER_DEFAULT_PATH = su_worker.SU_WORKER_DEFAULT_PATH

try:
    is_valid_su_worker = su_worker.validate_su_worker(TEST_BUILD_WORKER, SU_WORKER_DEFAULT_PATH)
except errors.BinstarError:
    is_valid_su_worker = False
standard_root_install = os.path.exists(SU_WORKER_DEFAULT_PATH)

class TestSuWorker(unittest.TestCase):
    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    @urlpatch 
    @patch('binstar_build_client.worker.su_worker.SuWorker')
    def test_su_worker(self, urls, SuWorker):
        '''Test su_worker CLI '''
        main(['--show-traceback', 'su_worker', 'username/queue-1', TEST_BUILD_WORKER], False)
        self.assertEqual(SuWorker().work_forever.call_count, 1)

    def test_validate_su_worker(self):
        '''Test su_worker is only run as root, with root python install'''
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
        self.assertEqual(getuid.call_count, 1)

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
            procs.append(sp.Popen(['su', '-c', 
                                   'sleep 10000', 
                                   '-', TEST_BUILD_WORKER]))
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
    
    def test_run(self):
        ok = ['echo','su_worker_test_ok']
        with patch.object(su_worker.SuWorker, 'su_with_env', return_value=ok) as su_with_env:
            with patch.object(su_worker.SuWorker, 'destroy_user_procs', return_value=True) as destroy_user_procs:
                with patch.object(su_worker.SuWorker, 'working_dir', return_value='.') as working_dir:
                    with patch.object(su_worker, 'validate_su_worker', return_value=True) as validate_su_worker:
                        worker = self.new_su_worker()
                        build_data = {} 
                        build_log = io.StringIO()
                        timeout = iotimeout = 200
                        script_filename = 'script'
                        exit_code = worker.run(build_data, script_filename, 
                                                  build_log, timeout, iotimeout,
                                                  api_token='api_token', 
                                                  git_oauth_token='git_oauth_token', 
                                                  build_filename=None, instructions=None)
                        build_log = build_log.getvalue()
                        self.assertIn('su_worker_test_ok', build_log)
                        self.assertEqual(exit_code, 0)
        self.assertEqual(su_with_env.call_count, 1)
        self.assertEqual(destroy_user_procs.call_count, 1)
        self.assertEqual(working_dir.call_count, 1)
        self.assertEqual(validate_su_worker.call_count, 1)

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

    def new_su_worker(self):
        args = Namespace()
        args.site = 'http://api.anaconda.org'
        args.token = None
        bs = get_binstar(args, cls=BinstarBuildAPI)
        return su_worker.SuWorker(bs, args, TEST_BUILD_WORKER, SU_WORKER_DEFAULT_PATH)

if __name__ == '__main__':
    unittest.main()
