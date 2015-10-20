import unittest
from binstar_build_client.worker.utils.timeout import Timeout

class Test(unittest.TestCase):


    def test_timeout(self):

        @Timeout(.1)
        def to():
            to.callback_called = True
            pass

        with to:
            while not to.timout_occurred:
                pass

        self.assertTrue(to.timout_occurred)
        self.assertTrue(to.callback_called)

    def test_timeout_2(self):
        ''
        @Timeout(2)
        def to():
            pass

        with to:
            pass

        self.assertFalse(to.timout_occurred)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_test_timer']
    unittest.main()
