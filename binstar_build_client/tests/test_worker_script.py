'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import Namespace
from glob import glob
import os
import yaml
from mock import patch, Mock, MagicMock
import unittest

from binstar_client import errors
from binstar_client.utils import get_binstar

from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.scripts.worker import main
from binstar_build_client.utils.worker_stats import worker_stats
from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client import worker
from binstar_build_client import BinstarBuildAPI

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
        if not os.path.exists(WorkerConfiguration.REGISTERED_WORKERS_DIR):
            os.mkdir(WorkerConfiguration.REGISTERED_WORKERS_DIR)
        super(Test, cls).setUpClass()

    def tearDown(self):

        for fn in glob(os.path.join(test_workers, '*')):
            os.unlink(fn)

        unittest.TestCase.tearDown(self)

    @urlpatch
    @patch('binstar_build_client.worker.register.WorkerConfiguration.register')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.deregister')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_register(self, load, deregister, register, urls):

        main(['register', 'username/queue-1'], False)
        self.assertEqual(urls.call_count, 1)

        main(['deregister', 'worker_id'], False)
        self.assertEqual(deregister.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.register.WorkerConfiguration.register')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.deregister')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_register_name(self, load, deregister, register, urls):

        main(['register', 'username/queue-1', '--name', 'myworker'], False)
        self.assertEqual(urls.call_count, 1)

        main(['deregister', 'myworker'], False)
        self.assertEqual(deregister.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.register.WorkerConfiguration.register')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.deregister')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_register_bad_name(self, load, deregister, register, urls):
        with self.assertRaises(errors.BinstarError):
            main(['register', 'username/queue-1', '--name','!bad-name'], False)

    @urlpatch
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    def test_register_duplicate_name(self, load, urls):
        registered = {}
        @classmethod
        def register_func(cls, *args, **kwargs):
            name = kwargs.get('name')
            if name in registered:
                raise errors.BinstarError('already registered {}'.format(registered))
            registered[name] = True
            args2 = [name] + list(args)
            return WorkerConfiguration(*args2)

        with patch.object(worker.register.WorkerConfiguration, 'register', new=register_func) as register:
            main(['register', 'username/queue-1', '--name', 'worker1'], False)
            self.assertEqual(registered, {'worker1': True})
            with self.assertRaises(errors.BinstarError):
                main(['register', 'username/queue-1', '--name', 'worker1'], False)


    @urlpatch
    @patch('binstar_build_client.worker.worker.Worker.work_forever')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    @patch('binstar_build_client.worker.worker.Worker.run')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.validate_worker_name')
    @patch('binstar_build_client.mixins.build_queue.BuildQueueMixin.upload_worker_stats')
    def test_worker_simple(self, upload, validate, run, load, loop, urls):

        main(['--show-traceback', 'worker', 'run', worker_data['worker_id']], False)

        self.assertEqual(loop.call_count, 1)

    @urlpatch
    @patch('binstar_build_client.worker.docker_worker.DockerWorker.work_forever')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.load')
    @patch('binstar_build_client.worker.docker_worker.DockerWorker.run')
    @patch('binstar_build_client.worker_commands.docker_run.docker')
    @patch('binstar_build_client.worker.docker_worker.docker')
    @patch('binstar_build_client.worker.docker_worker.kwargs_from_env')
    @patch('binstar_build_client.worker.register.WorkerConfiguration.validate_worker_name')
    @patch('binstar_build_client.mixins.build_queue.BuildQueueMixin.upload_worker_stats')
    def test_worker_simple_docker(self, upload, validate, kwargs_from_env, docker1, docker2, run, load, loop, urls):

        docker1.Client = docker2.Client = Mock()

        main(['--show-traceback', 'worker', 'docker_run', worker_data['worker_id']], False)

        self.assertEqual(loop.call_count, 1)

    @patch('binstar_build_client.worker.register.WorkerConfiguration.registered_workers')
    def test_duplicate_worker_name(self, registered):
        worker_configs = [Namespace(name='abc',
                          worker_id='id_' + worker,
                          username='user',
                          queue='queue',
                          platform='platform',
                          hostname='hostname',
                          dist='dist')  for worker in ('a', 'b')]

        for worker_config in worker_configs:
            worker_config.to_dict = lambda : worker_config.__dict__
        registered.return_value = iter(worker_configs)
        bs = get_binstar(Namespace(), cls=BinstarBuildAPI)
        with self.assertRaises(errors.BinstarError):
            WorkerConfiguration.validate_worker_name(bs, 'abc')

    def test_register_backwards_compat(self):

        worker_file = os.path.join(WorkerConfiguration.REGISTERED_WORKERS_DIR,
                                   'worker_name_1')
        worker_id = '123456789'
        worker_id_pid = '{}.123'.format(worker_id)
        with open(worker_file, 'w') as f:
            f.write(yaml.safe_dump({'worker_id': worker_id}))
        worker_id_to_name = WorkerConfiguration.backwards_compat_lookup()
        self.assertIn(worker_id, worker_id_to_name)
        if os.path.exists(worker_file):
            os.unlink(worker_file)
        self.assertEqual(worker_id_to_name[worker_id], 'worker_name_1')
        worker_id_to_name = WorkerConfiguration.backwards_compat_lookup()
        self.assertEqual(worker_id_to_name.get(worker_id, None), None)

    def test_register_backwards_compat_pid(self):
        '''Test .workers files that when yaml loaded
        will error out or not return a dict.'''
        folder = WorkerConfiguration.REGISTERED_WORKERS_DIR
        for f in os.listdir(folder):
            os.unlink(os.path.join(folder, f))
        test_cases = [
            ('worker1.123', ''),
            ('worker2.234', 'user99'), # su worker uses usernames in pid files
            ('worker3.1234', '{bad_dict: [abc,'), # this shouldn't happen but just in case
        ]
        for pid_file, content in test_cases:
            worker_id_pid = os.path.join(folder, pid_file)
            with open(worker_id_pid, 'w') as f:
                f.write(content)
        worker_id_to_name = WorkerConfiguration.backwards_compat_lookup()
        # the above should be len zero because folder started
        # empty and added only pid files.  No
        # worker yaml's that have worker_id's
        # in them were added. It should skip without error
        # over bad or irrelevant files (non-yaml worker configs)
        self.assertEqual(len(worker_id_to_name), 0)


if __name__ == '__main__':
    unittest.main()
