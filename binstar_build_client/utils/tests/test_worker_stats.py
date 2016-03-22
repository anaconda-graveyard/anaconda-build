import unittest
import mock
import os

from binstar_build_client.utils.worker_stats import worker_stats

expected_keys = {'win': set(('logicaldisk', 'systeminfo', 'wmic')),
                 'posix': set(('df',('vm_stat', 'meminfo'),
                               ))}

class Test(unittest.TestCase):
    def test_keys(self):
        stats = worker_stats()
        if os.name == 'nt':
            for key in expected_keys['win']:
                self.assertIn(key, stats)
        else:
            self.assertIn('df', stats)
            if 'vm_stat' in stats or 'meminfo' in stats:
                has_mem = True
            else:
                has_mem = False
            has_sys = False
            for key in ('yum', 'brew', 'dpkg', 'apt'):
                if key in stats:
                    has_sys = True
            self.assertTrue(has_mem)
            self.assertTrue(has_sys)
        for key, value in stats.items():
            self.assertEqual(sorted(value.keys()), ['cmd', 'out'])
        self.assertIn('conda list', stats)
        self.assertIn('conda env list', stats)
        self.assertIn('conda info', stats)
