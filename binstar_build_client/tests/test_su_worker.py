'''
Test worker.SuWorker.

This test is only run if user is root, there is a root python install, and there is a 
build user called test_build_worker.
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from mock import patch
import unittest

from binstar_build_client.scripts.build import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.worker.su_worker import (SuWorker, 
        validate_su_worker,
        SU_WORKER_DEFAULT_PATH)
import subprocess as sp 
import unittest
import sys
import os

TEST_BUILD_WORKER = 'test_build_worker'

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
    
if __name__ == '__main__':
    unittest.main()
       