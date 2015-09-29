'''
Test worker.SuWorker.

This test is only run if user is root, there is a root python install, and there is a 
build user called test_build_worker.
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import unittest
import subprocess as sp 
import unittest
import sys
import io
import os
import sys
import tempfile
import psutil
from argparse import Namespace
from mock import patch

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.scripts.build import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.worker.su_worker import (SuWorker, 
                                                   validate_su_worker,
                                                   SU_WORKER_DEFAULT_PATH)
from binstar_build_client.worker.su_worker import SuWorker, SU_WORKER_DEFAULT_PATH
from binstar_client.utils import get_binstar
from binstar_client.utils import get_config

TEST_BUILD_WORKER = 'test_build_worker'
args = Namespace()
vars(args).update({'queue': 'queue-1', 
                   'username':'username', 
                   'build_user': TEST_BUILD_WORKER})

try:
    is_valid_su_worker = validate_su_worker(TEST_BUILD_WORKER, SU_WORKER_DEFAULT_PATH)
except Exception as e:
    is_valid_su_worker = False

class TestSuWorker(unittest.TestCase):
    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    @urlpatch 
    @patch('binstar_build_client.commands.su_worker.SuWorker')
    def test_su_worker(self, urls, SuWorker):

        main(['--show-traceback', 'su_worker', 'username/queue-1', TEST_BUILD_WORKER], False)
        self.assertEqual(SuWorker().work_forever.call_count, 1)
    def test_validate_su_worker(self):
        import binstar_build_client.worker.su_worker as S
        old_is_root = S.is_root
        S.is_root = True 
        old_etc = S.has_etc_worker_skel
        S.has_etc_worker_skel = True 
        old_check_conda = S.check_conda_path
        S.check_conda_path = lambda build_user, python_install_dir: True 
        is_valid = S.validate_su_worker(TEST_BUILD_WORKER, sys.prefix)
        S.is_root = old_is_root
        S.has_etc_worker_skel = old_etc
        S.check_conda_path = old_check_conda
        self.assertTrue(is_valid)

    def cmd(self, args) :
        return sp.Popen(args, stdout=sp.PIPE, stderr=sp.PIPE)
    
    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    def test_destroy_user_procs(self):
        su_worker = self.new_su_worker()
        procs = []
        for new_proc in range(5):
            procs.append(self.cmd(['su', '-c', 
                                   'sleep 10000', 
                                   '-', TEST_BUILD_WORKER]))
        build_user_pids = [proc.pid for proc in procs]
        found_pids = self.find_test_worker_pids()
        for pid in build_user_pids:
            self.assertIn(pid, found_pids)
        su_worker.destroy_user_procs()
        found_pids = self.find_test_worker_pids()
        for pid in build_user_pids:
            self.assertNotIn(pid, found_pids)

    def find_test_worker_pids(self):
        found_pids = []
        for proc in psutil.process_iter():
            try:
                if hasattr(proc, 'username') and callable(proc.username):
                    is_worker_proc = proc.username() == TEST_BUILD_WORKER
                else:
                    is_worker_proc = proc.uids().real != 0 # approximate for test 
                if is_worker_proc:
                    found_pids.append(proc.pid())
            except psutil.AccessDenied:
                pass
        return found_pids
        
    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    def test_run(self):
        su_worker = self.new_su_worker()
        su_worker.working_dir = lambda x: os.path.expanduser('~{}'.format(TEST_BUILD_WORKER))
        su_worker.clean_home_dir()
        script_filename = os.path.join(su_worker.working_dir(None), 'test_run_script.sh')
        with open(script_filename, 'w') as f:
            f.write('''#!/bin/bash
                        for word in $*;
                            do 
                                echo ${word};
                            done"''')
        build_data = {} 
        build_log = io.StringIO()
        timeout = iotimeout = 200
        exit_code = su_worker.run(build_data, script_filename, build_log, timeout, iotimeout,
                      api_token='api_token', git_oauth_token='git_oauth_token', 
                      build_filename=None, instructions=None)
        build_log = build_log.getvalue()
        self.assertIn('api_token', build_log)
        self.assertIn('git_oauth_token', build_log)
        self.assertEqual(exit_code, 0)

    @unittest.skipIf(not is_valid_su_worker, 'Skipping as not valid su_worker')
    @unittest.skipIf(not os.path.exists(SU_WORKER_DEFAULT_PATH), 'Skipping non-default install')
    def test_clean_home_dir(self):    
        su_worker = self.new_su_worker()
        home_dir = os.path.expanduser('~{}'.format(TEST_BUILD_WORKER))
        to_be_removed = os.path.join(home_dir, 'to_be_removed')
        with open(to_be_removed, 'w') as f:
            f.write('to_be_removed')
        su_worker.clean_home_dir()
        sorted_home_dir = sorted(os.listdir(home_dir))
        sorted_etc_worker = sorted(os.listdir('/etc/worker-skel'))
        self.assertEqual(sorted_etc_worker, sorted_home_dir)

    def new_su_worker(self):
        args = Namespace()
        args.site = 'http://api.anaconda.org'
        args.token = None
        bs = get_binstar(args, cls=BinstarBuildAPI)
        return SuWorker(bs, args, TEST_BUILD_WORKER, SU_WORKER_DEFAULT_PATH)
        

if __name__ == '__main__':
    unittest.main()
       