'''
Created on Feb 18, 2014

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from mock import patch
import unittest
import os
import subprocess as sp

from binstar_build_client.scripts.build import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch
from binstar_build_client.worker.worker import get_my_procs

class Test(CLITestCase):


    @urlpatch
    @patch('binstar_build_client.commands.worker.Worker')
    def test_worker_simple(self, urls, Worker):

        main(['--show-traceback', 'worker', 'username/queue-1'], False)
        self.assertEqual(Worker().work_forever.call_count, 1)

    def test_get_my_procs(self):
        pids = []
        for repeat in range(5):
            proc = sp.Popen(['sleep', '10000'])
            pids.append(proc.pid)
        pids.append(os.getpid())
        my_pids = get_my_procs()
        for pid in pids:
            self.assertIn(pid, my_pids)
    
if __name__ == '__main__':
    unittest.main()
