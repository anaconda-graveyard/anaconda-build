'''
test_build_commands.py includes tests for commands
that start with:

anaconda build
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
from binstar_build_client.scripts.build import main
from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client import worker
from binstar_build_client import BinstarBuildAPI

class Test(CLITestCase):

    @property
    def conda_test_dir(self):
        d = os.path.dirname
        return os.path.join(d(d(d(d(__file__)))), 'test', 'conda')

    @urlpatch
    @patch('binstar_client.utils.get_binstar')
    def _tst_submit_git_url(self, bs,  urls, extra_args=None):

        args = ['submit', self.repo] + (extra_args or [])
        main(args, False)

    def test_submit_ok(self):
        self.repo = self.conda_test_dir
        self._tst_submit_git_url()

    @patch('binstar_build_client.build_commands.submit.tail_sub_build')
    def test_submit_tail(self, tail):
        self.repo = self.conda_test_dir
        self._tst_submit_git_url(extra_args=['-f'])
        self._tst_submit_git_url(extra_args=['--tail'])
        self._tst_submit_git_url(extra_args=['-f', '--sub-builds', '0', '1'])
        self.assertEqual(tail.call_count, 3)

if __name__ == '__main__':
    unittest.main()