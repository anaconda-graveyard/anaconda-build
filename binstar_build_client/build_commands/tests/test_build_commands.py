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
    #@patch('binstar_client.commands.login.interactive_login')
    #@patch('binstar_client.commands.login.interactive_get_token')
    @patch('binstar_client.utils.get_binstar')
    def _tst_submit_git_url(self, bs,  urls):#get_token, login,
        bs.user = lambda: {}
        args = ['submit', self.repo]
        main(args, False)

    def test_submit_git_url_ok(self):
        self.repo = 'https://github.com/conda/conda-recipes'
        self._tst_submit_git_url()

    def test_submit_git_url_no_github(self):
        self.repo = 'https://gitlab.com/conda/conda-recipes'
        with self.assertRaises(errors.UserError):
            self._tst_submit_git_url()

    def test_submit_git_url_with_dot(self):
        self.repo = 'http://github.com/PeterDSteinberg/myorg.package1'
        self._tst_submit_git_url()

    def test_submit_git_url_dots_in_branch(self):
        self.repo = 'https://github.com/PeterDSteinberg/myorg.package1/tree/mybranch.odd.name'
        self._tst_submit_git_url()
if __name__ == '__main__':
    unittest.main()
