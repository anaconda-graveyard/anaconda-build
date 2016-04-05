import unittest
import mock
from binstar_build_client.utils import get_conda_root_prefix, CONDA_EXE, get_conda_build_dir
import os

def mock_access(value):

    def _mock_access(dirname, _):
        return value
    return _mock_access

def mock_expanduser(path):
    return path

def list_dir(dirname):
    if dirname == '/a/bin':
        return [CONDA_EXE, 'not_conda']
    else:
        return ['not_conda']

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

        listdir.side_effect = list_dir

        prefix = get_conda_root_prefix()
        self.assertTrue(prefix in ('/a', "C:\\a"))


    @mock.patch.dict(os.environ, {'PATH': '/a/bin' + os.pathsep + '/b/bin'})
    @mock.patch('os.path.isdir')
    @mock.patch('os.listdir')
    @mock.patch('os.access')
    def test_get_conda_build_dir_root(self, access, listdir, isdir):

        listdir.side_effect = list_dir
        access.side_effect = mock_access(True)

        build_dir = get_conda_build_dir()

        self.assertEqual(build_dir, '/a/conda-bld/{platform}')

    @mock.patch.dict(os.environ, {'PATH': '/a/bin' + os.pathsep + '/b/bin'})
    @mock.patch('os.path.isdir')
    @mock.patch('os.listdir')
    @mock.patch('os.access')
    @mock.patch('os.path.expanduser')
    def test_get_conda_build_dir_user(self, expand_user, access, listdir, isdir):


        listdir.side_effect = list_dir
        access.side_effect = mock_access(False)
        expand_user.side_effect = mock_expanduser

        build_dir = get_conda_build_dir()

        self.assertEqual(build_dir, '~/conda-bld/{platform}')


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
