from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from mock import patch
import unittest

from binstar_build_client.scripts.build import main
from binstar_client.tests.fixture import CLITestCase
from binstar_client.tests.urlmock import urlpatch

import subprocess as sp 
import unittest
import sys

BUILD_WORKER_TEST = 'test_build_worker'

def cmd(c):
    out,err = sp.Popen(c, stdout=sp.PIPE,stderr=sp.PIPE).communicate()
    return out,err
is_root = cmd(['whoami'])[0].strip() == 'root'
is_root_install = '/opt/anaconda' in sys.prefix
has_build_worker = BUILD_WORKER_TEST in  cmd(['su','--login','-c','whoami', 
                             '-', BUILD_WORKER_TEST])[0].strip()

class TestSuWorker(unittest.TestCase):
    @unittest.skipIf(not is_root,
                     "not running as root")
    @unittest.skipIf(not is_root_install,'not an /opt/anaconda install')
    @unittest.skipIf(not has_build_worker,'does not have %s user' % BUILD_WORKER_TEST)
    @urlpatch 
    @patch('binstar_build_client.commands.su_worker.SuWorker')
    def test_worker_simple(self, urls, SuWorker):

        main(['--show-traceback', 'su_worker', 'username/queue-1', BUILD_WORKER_TEST], False)
        self.assertEqual(SuWorker().work_forever.call_count, 1)

if __name__ == '__main__':
    unittest.main()
       