'''
Created on Feb 22, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import codecs
import contextlib
import io
import logging
import mock
import shutil
from os.path import join, dirname
import os
import tempfile
import unittest

from binstar_client import tests

test_data = join(dirname(tests.__file__), 'data')

class CLITestCase(unittest.TestCase):

    def data_dir(self, filename):
        return join(test_data, filename)

    def setUp(self):

        self.get_config_patch = mock.patch('binstar_client.utils.get_config')
        self.get_config = self.get_config_patch.start()
        self.get_config.return_value = {}

        self.load_token_patch = mock.patch('binstar_client.utils.load_token')
        self.load_token = self.load_token_patch.start()
        self.load_token.return_value = '123'

        self.store_token_patch = mock.patch('binstar_client.utils.store_token')
        self.store_token = self.store_token_patch.start()

        self.setup_logging_patch = mock.patch('binstar_client.scripts.cli.setup_logging')
        self.setup_logging_patch.start()

        self.logger = logger = logging.getLogger('binstar')
        logger.setLevel(logging.INFO)
        self.stream = io.StringIO()
        self.hndlr = hndlr = logging.StreamHandler(stream=self.stream)
        hndlr.setLevel(logging.INFO)
        logger.addHandler(hndlr)


    def tearDown(self):
        self.setup_logging_patch.stop()
        self.get_config_patch.stop()
        self.load_token_patch.stop()
        self.store_token_patch.stop()

        self.logger.removeHandler(self.hndlr)


@contextlib.contextmanager
def mkdtemp():
    """Create a temporary directory that is removed after the context
    """
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)

def makedirs_ok_if_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def with_directory_contents(contents, func):
    with mkdtemp() as dirname:
        for filename, file_content in contents.items():
            path = os.path.join(dirname, filename)
            makedirs_ok_if_exists(os.path.dirname(path))
            with codecs.open(path, 'w', 'utf-8') as f:
                f.write(file_content)
        func(os.path.realpath(dirname))
