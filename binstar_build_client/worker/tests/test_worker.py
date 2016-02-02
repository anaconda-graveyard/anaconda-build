from __future__ import print_function, unicode_literals, absolute_import

from argparse import Namespace
from mock import Mock, patch
import io
import os
import psutil
import unittest
import sys

import requests

from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.utils.validate_procs import validate_procs
from binstar_client import errors
import tempfile


class MockWorker(Worker):
    def __init__(self):
        self.SLEEP_TIME = 0
        bs = Mock()
        bs.log_build_output.return_value = False
        args = Mock()
        args.status_file = None
        args.timeout = 100

        worker_config = WorkerConfiguration(
            'worker_name',
            'worker_id', 'username', 'queue',
            'test_platform', 'test_hostname', 'dist'
        )

        Worker.__init__(self, bs, worker_config, args)


class Test(unittest.TestCase):
    def test_handle_job(self):

        class MyWorker(MockWorker):
            build = Mock()
            build.return_value = False, 'success'
            download_build_source = Mock()
        worker = MyWorker()
        worker.args.push_back = False
        worker._handle_job({'job':{'_id':'test_job_id'}})
        self.assertEqual(worker.build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_args[1], {'status': 'success', 'failed': False})

    def test_failed_job(self):

        class MyWorker(MockWorker):
            build = Mock()
            build.side_effect = Exception("This is an expected test error")

        worker = MyWorker()
        worker.args.push_back = False

        worker._handle_job({'job':{'_id':'test_job_id'}})

        self.assertEqual(worker.build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_count, 1)
        self.assertEqual(worker.bs.fininsh_build.call_args[1], {'status': 'error', 'failed': True})


    def test_download_build_source(self):

        worker = MockWorker()
        expected = b"build source"
        worker.bs.fetch_build_source.return_value = io.BytesIO(expected)


        filename = worker.download_build_source(tempfile.mkdtemp(), 'job_id')
        self.assertTrue(os.path.isfile(filename))
        self.addCleanup(os.unlink, filename)

        with open(filename, 'rb') as fd:
            data = fd.read()
        self.assertEqual(data, expected)


    def test_job_loop(self):
        worker = MockWorker()
        worker.args.one = True
        worker.bs.pop_build_job.return_value = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        jobs = list(worker.job_loop())
        self.assertEqual(len(jobs), 1)

    def test_job_loop_error(self):

        worker = MockWorker()
        worker.args.one = False
        worker.bs.pop_build_job.return_value = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}

        with self.assertRaises(TypeError):
            for job in worker.job_loop():
                raise TypeError("Expected Error")

    def test_job_loop_expected_errors(self):
        worker = MockWorker()
        worker.write_status = Mock()
        worker.args.one = False
        exceptions = [
            requests.ConnectionError(),
            errors.ServerError("error"),
            errors.NotFound("not found")
        ]
        def exception_factory(a, b, c, exceptions=exceptions):
            """
                raises each of the exceptions in order
                NotFound exception should break the loop
                The others should just trigger another iteration
            """
            raise exceptions.pop(0)

        worker.bs.pop_build_job.side_effect = exception_factory

        with self.assertRaises(errors.NotFound):
            for i, job in enumerate(worker.job_loop()):
                if i > 3:
                    raise RuntimeError('Ran loop more times than expected')

            worker.write_status.assert_called_with(False, "Trouble connecting to binstar")
            worker.write_status.assert_called_with(False, "Server error")
            worker.write_status.assert_called_with(False, "worker not found")


    def test_job_context(self):

        worker = MockWorker()
        worker.args.one = False
        job_data = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        journal = io.StringIO()

        with worker.job_context(journal, job_data):
            pass

        value = journal.getvalue()
        expected = 'starting build, test_job_id, job_name\nfinished build, test_job_id, job_name\n'
        self.assertEqual(value, expected)

    def test_job_context_error(self):

        worker = MockWorker()
        worker.args.one = False
        job_data = {'job':{'_id':'test_job_id'}, 'job_name':'job_name'}
        journal = io.StringIO()

        with worker.job_context(journal, job_data):
            raise TypeError("hai -- Expected Error")

        value = journal.getvalue()
        expected = 'starting build, test_job_id, job_name\nbuild errored, test_job_id, job_name\n'
        self.assertEqual(value, expected)

    def test_worker_conflicts_check(self):
        def mock_proces_iter():
            n = Namespace()
            n.pid = 1234
            n.cmdline = lambda: [sys.prefix]
            yield n

        with patch.object(psutil, 'process_iter', mock_proces_iter):
            with patch.object(os, 'name', new_callable=lambda: 'nt'):
                procs_on_wrong_python = validate_procs()
                self.assertEqual(len(procs_on_wrong_python), 1)
        def mock_no_conflict():
            n=Namespace()
            n.pid = 1234,
            n.cmdline = lambda: "C:\\Not-needed"
            yield n

        with patch.object(psutil,'process_iter', mock_no_conflict):
            with patch.object(os, 'name', new_callable=lambda:'nt'):
                self.assertEqual(validate_procs(), [])

if __name__ == '__main__':
    unittest.main()
