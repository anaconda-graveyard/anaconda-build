'''
Created on Feb 12, 2015

@author: sean
'''
import unittest
import mock
from binstar_build_client.utils import get_conda_root_prefix, CONDA_EXE
import os
class Test(unittest.TestCase):

    @mock.patch.dict(os.environ, {'PATH': '/does_not_exist!!'})
    def test_path_does_not_exist(self):
        prefix = get_conda_root_prefix()
        self.assertIsNone(prefix)

    @mock.patch.dict(os.environ, {'PATH': '/a/bin' + os.pathsep + '/b/bin'})
    @mock.patch('os.path.isdir')
    @mock.patch('os.listdir')
    def test_finds_conda(self, listdir, isdir):
        listdir.return_value = [CONDA_EXE, 'not_conda']
        prefix = get_conda_root_prefix()
        self.assertEqual(prefix, '/a')




if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
