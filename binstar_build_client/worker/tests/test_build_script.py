from __future__ import print_function, unicode_literals, absolute_import

from os import path
import os
from subprocess import Popen, PIPE, STDOUT
import unittest
import tempfile


from binstar_build_client.worker_commands.register import get_platform
from binstar_build_client.worker.utils.script_generator import gen_build_script

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

        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir, tempdir, build_data, ignore_setup_build=True)
        self.addCleanup(os.unlink, script_filename)

        build_tarball = path.join(path.dirname(__file__), 'data', 'does_not_exist.tar.bz2')

        p0 = Popen([script_filename, '--build-tarball', build_tarball], stdout=PIPE, stderr=STDOUT)
        self.assertEqual(p0.wait(), 11)
        p0.stdout.close()


    def test_instructions_success(self):

        build_data = default_build_data()
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir, tempdir, build_data,
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
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
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
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
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
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
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
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
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
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
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
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
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

    def test_conda_npy(self):
        build_data = default_build_data()
        build_data['build_item_info']['engine'] = 'numpy=1.9'
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(tempdir,
                                           tempdir,
                                           build_data,
                                           ignore_setup_build=False,
                                           ignore_fetch_build_source=True)

        self.addCleanup(os.unlink, script_filename)
        with open(script_filename, 'r') as f:
            script_lines = [_.strip() for _ in f.readlines()]
        relates_to_npy = [idx for idx, line in enumerate(script_lines) if 'NUMPY' in line or 'NPY' in line]
        # Test that the export showed up at top
        if script_lines[relates_to_npy[0]].startswith(('export', 'set')):
            exported = relates_to_npy.pop(0)
            self.assertIn('=19', script_lines[exported])
            self.assertIn('CONDA_NPY', script_lines[exported])

        # Test that the other type of CONDA_NPY identification
        # can run without error
        other_numpy = "\n".join(script_lines[min(relates_to_npy): max(relates_to_npy) + 1])

        script_filename = os.path.join(tempdir, 'numpy_script')
        if os.name == 'nt':
            script_filename += '.bat'
            args = ['cmd', '/c', 'call', script_filename]
        else:
            script_filename += '.sh'
            args = ['bash', script_filename]
        with open(script_filename, 'w') as f:
            f.write(other_numpy)
        self.addCleanup(os.unlink, script_filename)

        proc = Popen(args, stdout=PIPE, stderr=STDOUT, cwd=tempdir)
        output = proc.stdout.read().decode().splitlines()
        npy = len([line for line in output if 'CONDA_NPY=' in line])
        self.assertTrue(npy >= 1)

    def test_env_envvars(self):
        'Test env or envvars can be used in .binstar.yml'
        build_data = default_build_data()
        for name in ('env', 'envvars'):
            build_data['build_item_info'][name] = {'ENVIRONMENT_VARIABLE': '1'}
            tempdir = tempfile.mkdtemp()
            script_filename = gen_build_script(tempdir,
                                               tempdir,
                                                 build_data,
                                                 ignore_setup_build=True,
                                                 ignore_fetch_build_source=True)
            self.addCleanup(os.unlink, script_filename)
            contents = open(script_filename).read()
            self.assertIn('ENVIRONMENT_VARIABLE=', contents)
            build_data['build_item_info'].pop(name)


class TestContent(unittest.TestCase):

    def generate_script(self, build_data, **kwargs):
        tempdir = tempfile.mkdtemp()
        script_filename = gen_build_script(
            tempdir,
            tempdir,
            build_data,
            **kwargs)

        self.addCleanup(os.unlink, script_filename)
        with open(script_filename, 'r') as script:
            return script.read()

    def test_normal_upload(self):
        build_data = default_build_data()
        build_data['build_item_info']['instructions']['build_targets'] = ['README.md']

        content = self.generate_script(build_data)

        self.assertIn('README.md', content)
        self.assertNotIn('--force', content)

    def test_force_upload(self):
        build_data = default_build_data()
        build_data['build_item_info']['instructions']['build_targets'] = {'files': 'README.md', 'force_upload': True}

        content = self.generate_script(build_data)

        self.assertIn('README.md', content)
        self.assertIn('--force', content)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_timeout']
    unittest.main()
