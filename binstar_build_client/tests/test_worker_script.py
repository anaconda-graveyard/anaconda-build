'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import yaml
from mock import patch
import unittest

from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.scripts.worker import main
from binstar_build_client.worker.register import WorkerConfiguration
from glob import glob
from binstar_client import errors

test_workers = os.path.abspath('./test-workers')
worker_data = {
               'username': 'username',
               'queue': 'queue-1',
               'platform': 'platform',
               'worker_id': 'worker_id',
               'hostname': 'localhost',
               'dist': 'dist',
            }

class Test(CLITestCase):

    @classmethod
    def setUpClass(cls):
        WorkerConfiguration.REGISTERED_WORKERS_DIR = test_workers
        super(Test, cls).setUpClass()

    def tearDown(self):

        for fn in glob(os.path.join(test_workers, '*')):
            os.unlink(fn)

        unittest.TestCase.tearDown(self)

    @urlpatch
    @patch('binstar_build_client.worker.register.WorkerConfiguration.register')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.deregister')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_register(self, load, deregister, urls, register):

        main(['register', 'username/queue-1'], False)
        self.assertEqual(register.call_count, 1)

        main(['deregister', 'worker_id'], False)
        self.assertEqual(deregister.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.worker.Worker.work_forever')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    @patch('binstar_build_client.worker.worker.Worker.run')
    def test_worker_simple(self, run, load, loop, urls):

        main(['--show-traceback', 'worker', 'run', worker_data['worker_id']], False)

        self.assertEqual(loop.call_count, 1)

if __name__ == '__main__':
    unittest.main()
