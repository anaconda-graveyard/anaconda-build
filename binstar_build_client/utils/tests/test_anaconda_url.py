import binstar_build_client.utils
import doctest


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(binstar_build_client.utils))
    return tests
