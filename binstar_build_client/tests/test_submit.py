import contextlib
import io
import json
import logging
import unittest

from binstar_client.scripts.cli import main
from binstar_client.tests.fixture import CLITestCase

from binstar_build_client.tests.urlmock import urlpatch


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
    @urlpatch
    def test_simple(self, urls):
        urls.register(path='/build/me/p1/trigger', method='POST', content='{"build_no":"1.0"}', status=201)

        with capture_logging('binstar.build') as output:
            main(['build', 'trigger', 'me/p1'], False)

        out = output.getvalue()

        self.assertIn('https://anaconda.org/me/p1/builds/matrix/1.0', out)

    @urlpatch
    def test_tags(self, urls):
        trigger = urls.register(path='/build/me/p1/trigger', method='POST', content='{"build_no":"1.0"}', status=201)

        main(['build', 'trigger', '--buildhost', 'host1', '--dist', 'ubuntu', '--platform', 'linux-64', 'me/p1'], False)

        parameters = json.loads(trigger.req.body)

        self.assertIn('queue_tags', parameters)
        self.assertIn('filter_platform', parameters)
        self.assertEqual(parameters['filter_platform'], 'linux-64')
        self.assertItemsEqual(parameters['queue_tags'], ['dist:ubuntu', 'hostname:host1'])


if __name__ == '__main__':
    unittest.main()
