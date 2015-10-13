'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import tempfile
import yaml
from mock import patch
import unittest

from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.scripts.worker import main
from binstar_build_client.worker.register import (REGISTERED_WORKERS_DIR,
                                                  Registration)
from binstar_build_client.worker.worker import Worker
worker_data = {'cwd': '.',
               'output': os.path.join(REGISTERED_WORKERS_DIR, 'worker_id'),
               'username': 'username',
               'queue': 'queue-1',
               'conda_build_dir': 'conda_build_dir',
               'site': 'http://api.anaconda.org',
               'token': 'token',
               'platform': 'platform',
               'worker_id': 'worker_id',
               'status_file': 'status_file',
               'hostname': 'localhost',
               'dist': 'dist',
               'timeout': 1000,
            }

class Test(CLITestCase):


    @urlpatch
    @patch('binstar_build_client.worker.register.register_worker')
    def test_register(self, urls, register_worker):

        main(['register', 'username/queue-1','--cwd','.'], False)
        self.assertEqual(register_worker.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.register.deregister_worker')
    def test_deregister_from_config(self, urls, deregister_worker):

        with open(worker_data['output'], 'w') as f:
            f.write(yaml.dump(worker_data))
        main(['deregister', worker_data['output']], False)
        self.assertEqual(deregister_worker.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.register.deregister_worker')
    def test_deregister_from_id(self, urls, deregister_worker):

        main(['deregister', worker_data['worker_id']], False)
        self.assertEqual(deregister_worker.call_count, 1)


    @urlpatch
    def test_worker_simple(self, urls):
        with patch.object(Registration, 'load', return_value=Registration(worker_data)) as load:
            with patch.object(Registration, 'clean_workers_dir', return_value=True) as clean:
                with patch.object(Registration, 'assert_is_not_running', return_value=True) as running:
                    with patch.object(Worker, '_build_loop', return_value=True) as loop:
                        with open(worker_data['output'], 'w') as f:
                            f.write(yaml.dump(worker_data))
                        main(['--show-traceback', 'run', worker_data['worker_id']], False)
        self.assertEqual(loop.call_count, 1)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(clean.call_count, 1)
        self.assertEqual(running.call_count, 1)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(worker_data['output']):
            os.remove(worker_data['output'])

if __name__ == '__main__':
    unittest.main()
