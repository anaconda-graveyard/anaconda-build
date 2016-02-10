from __future__ import print_function, unicode_literals, absolute_import

from subprocess import Popen, PIPE, STDOUT
import unittest

from binstar_build_client.worker_commands.register import get_platform
from binstar_build_client.worker.utils.script_generator import gen_build_script
from os import path
import os
import tempfile

def default_build_data():
    return {
              'build_info':
                {'api_endpoint': 'api_endpoint',
                 'build_no': 1,
                 '_id':'build_id',
                 },
              'build_item_info':
                {'platform': get_platform(),
                 'engine': 'python',
                 'build_no': '1.0',
                 'sub_build_no': 0,
                 'instructions': {
                                  'install':'echo UNIQUE INSTALL MARKER',
                                  'test': 'echo UNIQUE TEST MARKER',
                                  'before_script': 'echo UNIQUE BEFORE SCRIPT MARKER',
                                  'script': 'echo UNIQUE SCRIPT MARKER',
                                  'after_failure': 'echo UNIQUE AFTER FAILURE MARKER',
                                  'after_error': 'echo UNIQUE AFTER ERROR MARKER',
                                  'after_success': 'echo UNIQUE AFTER SUCCESS MARKER',
                                  'after_script': 'echo UNIQUE AFTER SCRIPT MARKER',

                                  },
                 },
              'job':
                {'_id': 'test_gen_build_script'},
              'owner': {'login': 'me'},
              'package': {'name': 'the_package'},

              }

class Test(unittest.TestCase):

    def assertInOrdered(self, lst, container):
        container_orig = container
        while lst:
            item = lst.pop(0)
            index = container.find(item)
            if index < 0:
                if item in container_orig:
                    msg = "String %r is out of order in the given sequence" % (item)
                else:
                    msg = "String %r not found in output" % (item)
                assert False, msg
            container = container[index + len(item):]


    def test_bad_tarball(self):
        build_data = default_build_data()

        script_filename = gen_build_script(tempfile.mkdtemp(), build_data, ignore_setup_build=True)
        self.addCleanup(os.unlink, script_filename)

        build_tarball = path.join(path.dirname(__file__), 'data', 'does_not_exist.tar.bz2')

        p0 = Popen([script_filename, '--build-tarball', build_tarball], stdout=PIPE, stderr=STDOUT)
        self.assertEqual(p0.wait(), 11)
        p0.stdout.close()


    def test_instructions_success(self):

        build_data = default_build_data()
        script_filename = gen_build_script(tempfile.mkdtemp(), build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)

        self.addCleanup(os.unlink, script_filename)
        p0 = Popen([script_filename], stdout=PIPE, stderr=STDOUT)
        return_code = p0.wait()
        self.assertEqual(return_code, 0,)
        output = p0.stdout.read().decode()
        self.assertIn("Exit BINSTAR_BUILD_RESULT=success", output)

        self.assertInOrdered(['UNIQUE INSTALL MARKER',
                              'UNIQUE TEST MARKER',
                              'UNIQUE BEFORE SCRIPT MARKER',
                              'UNIQUE SCRIPT MARKER',
                              'UNIQUE AFTER SUCCESS MARKER',
                              'UNIQUE AFTER SCRIPT MARKER',
                              ], output)
        p0.stdout.close()

    def test_instructions_error(self):

        build_data = default_build_data()
        build_data['build_item_info']['instructions']['install'] = 'invalid_command'
        script_filename = gen_build_script(tempfile.mkdtemp(),
                                           build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)

        self.addCleanup(os.unlink, script_filename)
        p0 = Popen([script_filename], stdout=PIPE, stderr=STDOUT)
        return_code = p0.wait()
        output = p0.stdout.read().decode()
        self.assertEqual(return_code, 11)

        self.assertIn("Exit BINSTAR_BUILD_RESULT=error", output)

        self.assertInOrdered([
                              'UNIQUE AFTER ERROR MARKER',
                              'UNIQUE AFTER SCRIPT MARKER',
                              ], output)
        p0.stdout.close()

    def test_instructions_failure(self):

        build_data = default_build_data()
        build_data['build_item_info']['instructions']['test'] = 'invalid_command'
        script_filename = gen_build_script(tempfile.mkdtemp(),
                                           build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)

        self.addCleanup(os.unlink, script_filename)
        p0 = Popen([script_filename], stdout=PIPE, stderr=STDOUT)
        return_code = p0.wait()
        output = p0.stdout.read().decode()
        self.assertEqual(return_code, 12)

        self.assertIn("Exit BINSTAR_BUILD_RESULT=failure", output)

        self.assertInOrdered(['UNIQUE INSTALL MARKER',
                              'UNIQUE AFTER FAILURE MARKER',
                              'UNIQUE AFTER SCRIPT MARKER',
                              ], output)

        p0.stdout.close()

    def test_instructions_failure2(self):

        build_data = default_build_data()
        build_data['build_item_info']['instructions']['script'] = 'invalid_command'
        script_filename = gen_build_script(tempfile.mkdtemp(),
                                           build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)

        self.addCleanup(os.unlink, script_filename)
        p0 = Popen([script_filename], stdout=PIPE, stderr=STDOUT)
        return_code = p0.wait()
        output = p0.stdout.read().decode()
        self.assertEqual(return_code, 12)

        self.assertIn("Exit BINSTAR_BUILD_RESULT=failure", output)

        self.assertInOrdered(['UNIQUE INSTALL MARKER',
                              'UNIQUE TEST MARKER',
                              'UNIQUE AFTER FAILURE MARKER',
                              'UNIQUE AFTER SCRIPT MARKER',
                              ], output)
        p0.stdout.close()

    def test_build_target_channels(self):
        build_data = default_build_data()
        build_data['build_item_info']['instructions']['build_targets'] = {
            'files': 'output_file',
            'channels': ['foo'],
        }
        script_filename = gen_build_script(tempfile.mkdtemp(),
                                           build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)
        self.addCleanup(os.unlink, script_filename)

        with open(script_filename, 'r') as script_file:
            script_content = script_file.read()

        self.assertIn("--label foo", script_content)

    def test_build_channels(self):
        build_data = default_build_data()
        build_data['build_info']['channels'] = ['foo']
        build_data['build_item_info']['instructions']['build_targets'] = {
            'files': 'output_file',
        }
        script_filename = gen_build_script(tempfile.mkdtemp(),
                                           build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)
        self.addCleanup(os.unlink, script_filename)

        with open(script_filename, 'r') as script_file:
            script_content = script_file.read()

        self.assertIn("--label foo", script_content)

    def test_working_dir(self):
        build_data = default_build_data()
        build_data['build_info']['channels'] = ['foo']
        build_data['build_item_info']['instructions']['build_targets'] = {
            'files': 'output_file',
        }
        script_filename = gen_build_script(tempfile.mkdtemp(),
                                           build_data,
                                           ignore_setup_build=True,
                                           ignore_fetch_build_source=True)
        self.addCleanup(os.unlink, script_filename)

        with open(script_filename, 'r') as script_file:
            script_content = script_file.read()

        self.assertIn("BUILD_ENV_PATH=", script_content)
        line = [line for line in script_content.splitlines() if 'BUILD_ENV_PATH=' in line]
        build_env_path = line[0].split('=')[-1].strip()
        if os.name == 'nt':
            self.assertEqual(build_env_path, '%WORKING_DIR%\env"')
        else:
            self.assertEqual(build_env_path, '"${WORKING_DIR}/env"')
    @unittest.skipIf(not os.name == 'nt', "Windows only")
    def test_conda_npy_win(self):
        bat_file = """
set HAS_NUMPY=0 & conda list | findstr numpy && set HAS_NUMPY=1
    if "%HAS_NUMPY%" == "1" (
         python -c "import sys;import numpy;sys.stdout.write(''.join(numpy.__version__.split('.')[:2]))"  > %TEMP%\CONDA_NPY
         set /p CONDA_NPY=<%TEMP%\CONDA_NPY
    )
echo CONDA_NPY %CONDA_NPY%
"""
        fname = os.path.abspath('numpyscript.bat')
        with open(fname, 'w') as f:
            f.write(bat_file)
        self.addCleanup(os.unlink, bat_file)
        proc = Popen([fname],
                     stdout=PIPE,
                     stderr=PIPE,
                     cwd='.')
        proc.wait()
        out = proc.stdout.read().decode().splitlines()[-1]
        try:
            import numpy
            has_numpy = True
            conda_npy = "".join(numpy.__version__.split('.')[:2])
        except ImportError:
            has_numpy = False
        no_numpy = not out.replace('CONDA_NPY').strip()
        if no_numpy:
            self.assertFalse(has_numpy)
        else:
            self.assertTrue(has_numpy)
            conda_npy_read = out.split()[-1].strip()
            self.assertEqual(conda_npy, conda_npy_read)

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_timeout']
    unittest.main()
