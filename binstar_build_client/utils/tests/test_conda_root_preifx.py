import unittest
import mock
from binstar_build_client.utils import get_conda_root_prefix, CONDA_EXE
import os
class Test(unittest.TestCase):

    @mock.patch.dict(os.environ, {'PATH': '/does_not_exist!!'})
    @mock.patch('os.listdir')
    def test_path_does_not_exist(self, listdir):
        listdir.return_value = []
        prefix = get_conda_root_prefix()
        self.assertIsNone(prefix)

    @mock.patch.dict(os.environ, {'PATH': '/a/bin' + os.pathsep + '/b/bin'})
    @mock.patch('os.path.isdir')
    @mock.patch('os.listdir')
    def test_finds_conda(self, listdir, isdir):

        def list_dir(dirname):
            print("dirname", dirname)
            if dirname == '/a/bin':
                return [CONDA_EXE, 'not_conda']
            else:
                return ['not_conda']

        listdir.side_effect = list_dir

        prefix = get_conda_root_prefix()
        self.assertTrue(prefix in ('/a', "C:\\a"))




if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
