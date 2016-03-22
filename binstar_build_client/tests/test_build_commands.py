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


    @urlpatch
    @patch('binstar_client.Binstar')
    @patch('binstar_client.Binstar.user')
    @patch('binstar_client.Binstar.package')
    @patch('binstar_build_client.mixins.build.BuildMixin.submit_for_url_build')
    @patch('binstar_build_client.mixins.build.BuildMixin.submit_for_build')
    def _tst_submit(self, submit, submit_url, bs, package, user, urls, extra_args=None):
        bs.user = lambda :{}
        args = ['submit', self.repo] + (extra_args or [])
        main(args, False)

    def test_submit_ok(self):
        self.repo = './'
        self._tst_submit()

    @patch('os.path.isfile')
    @patch('binstar_build_client.build_commands.submit.tail_sub_build')
    def test_submit_tail(self, tail, isfile):
        self.repo = './'
        self._tst_submit(extra_args=['-f'])
        self._tst_submit(extra_args=['--tail'])
        self._tst_submit(extra_args=['-f', '--sub-builds', '0', '1'])
        self.assertEqual(tail.call_count, 3)

    @patch('os.path.isfile')
    def test_submit_ok(self, isfile):
        self.repo = 'https://github.com/conda/conda-recipes'
        self._tst_submit()

    def test_submit_no_github(self):
        self.repo = 'https://gitlab.com/conda/conda-recipes'
        with self.assertRaises(errors.UserError):
            self._tst_submit()

    def test_submit_with_dot(self):
        self.repo = 'http://github.com/PeterDSteinberg/myorg.package1'
        self._tst_submit()

    def test_submit_dots_in_branch(self):
        self.repo = 'https://github.com/PeterDSteinberg/myorg.package1/tree/mybranch.odd.name'
        self._tst_submit()

    @urlpatch
    @patch('binstar_build_client.mixins.build_queue.BuildQueueMixin.build_backlog')
    def test_backlog(self, backlog, urls):
        main(['backlog', 'user/queue'], False)

    @urlpatch
    @patch('binstar_build_client.mixins.build.BuildMixin.tail_build')
    def test_tail(self, tail, urls):
        main(['tail', '-f', 'user/package', '0.1'], False)

    @urlpatch
    @patch('binstar_build_client.mixins.build_queue.BuildQueueMixin.add_build_queue')
    def test_queue(self, add_build_queue, urls):
        main(['queue', '--create', 'user/queue'], False)

    @urlpatch
    @patch('binstar_client.Binstar.package')
    @patch('binstar_build_client.mixins.build.BuildMixin.add_ci')
    def test_save(self, add_ci, package, urls):
        main(['save', 'https://github.com/user/package.name',
              '--package', 'user/package.name'], False)

    def test_save_bad_url(self):
        with self.assertRaises(errors.BinstarError):
            main(['save', 'https://not-github.com/user/package.name',
                  '--package', 'user/package.name'], False)

if __name__ == '__main__':
    unittest.main()
