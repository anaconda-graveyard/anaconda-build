import cgi
import contextlib
import io
import json
import logging
import subprocess
import tarfile
import unittest

from binstar_client.scripts.cli import main
from binstar_build_client.tests.fixture import CLITestCase
from binstar_build_client.tests import fixture
from binstar_build_client.tests import urlmock


@contextlib.contextmanager
def capture_logging(logger_name):
    output = io.StringIO()
    logger = logging.getLogger(logger_name)
    handler = logging.StreamHandler(output)
    formatter = logging.Formatter(u'%(message)s')
    logger.addHandler(handler)
    handler.setFormatter(formatter)

    yield output


class Test(CLITestCase):
    @urlmock.urlpatch
    def test_simple(self, urls):
        urls.register(path='/build/me/p1/trigger', method='POST', content='{"build_no":"1.0"}', status=201)

        with capture_logging('binstar.build') as output:
            main(['build', 'trigger', 'me/p1'], False)

        out = output.getvalue()

        self.assertIn('https://anaconda.org/me/p1/builds/matrix/1.0', out)

    @urlmock.urlpatch
    def test_tags(self, urls):
        trigger = urls.register(path='/build/me/p1/trigger', method='POST', content='{"build_no":"1.0"}', status=201)

        main(['build', 'trigger', '--buildhost', 'host1', '--dist', 'ubuntu', '--platform', 'linux-64', 'me/p1'], False)

        parameters = json.loads(trigger.req.body)

        self.assertIn('queue_tags', parameters)
        self.assertIn('filter_platform', parameters)
        self.assertEqual(parameters['filter_platform'], 'linux-64')
        self.assertEqual(set(parameters['queue_tags']), {'dist:ubuntu', 'hostname:host1'})


class TestUpload(CLITestCase):

    def setUp(self):
        CLITestCase.setUp(self)
        self.urls = urls = urlmock.Registry()
        self.urls.__enter__()

        urls.register(path='/package/u1/testpkg', content='{"name":"testpkg"}')

        stage_data = {
            "post_url": "http://localhost/build/u1/testpkg/upload",
            "form_data": {},
            "submit_data": {},
            "basename": "testpkg-basename",
            "build_id": "1.0",
            "build_no": "1.0",
        }
        urls.register(path='/build/u1/testpkg/stage', content=json.dumps(stage_data), method='POST')

        def read_body():
            content = io.BytesIO(upload.req.body.read())
            # TODO: find a simpler way to read multipart form data
            env = {
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': upload.req.headers['content-type'],
            }
            env = cgi.parse(content, env)
            self.fileobj = io.BytesIO(env['file'][0])

        upload = urls.register(path='/build/u1/testpkg/upload', content='', method='POST', status=201, side_effect=read_body)
        urls.register(path='/build/u1/testpkg/commit/1.0', content='{"build_no":"1.0"}', method='POST', status=201)

    def tearDown(self):
        CLITestCase.tearDown(self)
        self.urls.__exit__()

    def test_no_scm(self):

        def test_include(tempdir):
            main(['build', 'submit', tempdir], False)

            with tarfile.open(name='testpkg', fileobj=self.fileobj) as tf:
                files = set(tf.getnames())
            self.assertEqual({'.', './.binstar.yml', './.gitignore', './IGNORED', './README'}, files)

        fixture.with_directory_contents({
            '.binstar.yml': 'package: testpkg\nuser: u1',
            '.gitignore': 'IGNORED',
            'IGNORED': 'this should not be uploaded',
            'README': 'this should be uploaded'
        }, test_include)

    def test_git(self):

        def test_ignore(tempdir):
            subprocess.check_call(['git', 'init', tempdir])
            subprocess.check_call(['git', 'add', '.'], cwd=tempdir)
            subprocess.check_call(['git', 'commit', '-m', 'Initial commit'], cwd=tempdir)
            main(['build', 'submit', tempdir], False)

            with tarfile.open(name='testpkg', fileobj=self.fileobj) as tf:
                files = set(tf.getnames())

            self.assertIn('./.git', files, 'The git directory should be uploaded')
            self.assertIn('./README', files)
            self.assertIn('./.binstar.yml', files)
            self.assertIn('./.gitignore', files)
            self.assertNotIn('./IGNORED', files)

        fixture.with_directory_contents({
            '.binstar.yml': 'package: testpkg\nuser: u1',
            '.gitignore': 'IGNORED',
            'IGNORED': 'this should not be uploaded',
            'README': 'this should be uploaded'
        }, test_ignore)


if __name__ == '__main__':
    unittest.main()
