'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import os
import yaml
from mock import patch
import os
import subprocess as sp
import unittest

from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.worker.worker import get_my_procs
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
    def test_register(self, urls):

        register = urls.register(method='POST', path='/build-worker/username/queue-1', content='{"worker_id": "worker_id"}')

        main(['register', 'username/queue-1'], False)
        self.assertEqual(register.called, 1)

        deregister = urls.register(method='DELETE', path='/build-worker/username/queue-1/worker_id')


        main(['deregister', 'worker_id'], False)
        self.assertEqual(register.called, 1)
        self.assertEqual(deregister.called, 1)

    @urlpatch
    @patch('binstar_build_client.worker.worker.Worker.work_forever')
    def test_worker_simple(self, urls, loop):

        with self.assertRaises(errors.BinstarError):
            main(['--show-traceback', 'worker', 'run', worker_data['worker_id']], False)

        self.assertEqual(loop.call_count, 0)

        worker_config = WorkerConfiguration('worker_name', 'worker_id', 'username', 'queue', 'platform', 'hostname', 'dist')
        worker_config.save()
        main(['--show-traceback', 'worker', 'run', 'worker_name'], False)
        self.assertEqual(loop.call_count, 1)


    def test_get_my_procs(self):
        pids = []
        procs = []
        try:
            for repeat in range(5):
                proc = sp.Popen(['sleep', '100'])
                procs.append(proc)
                pids.append(proc.pid)
            pids.append(os.getpid())
            my_pids = get_my_procs()
            for pid in pids:
                self.assertIn(pid, my_pids)
        finally:
            for proc in procs:
                proc.kill()

if __name__ == '__main__':
    unittest.main()
