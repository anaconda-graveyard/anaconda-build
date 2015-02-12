'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from mock import patch
import unittest

from binstar_build_client.scripts.build import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch


class Test(CLITestCase):


    @urlpatch
    @patch('binstar_build_client.commands.worker.Worker')
    def test_worker_simple(self, urls, Worker):

        main(['--show-traceback', 'worker', 'username/queue-1'], False)
        self.assertEqual(Worker().work_forever.call_count, 1)

if __name__ == '__main__':
    unittest.main()
