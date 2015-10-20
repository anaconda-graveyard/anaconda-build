import time

class MockProcess(object):
    class MockStdOut(object):
        def __init__(self, limit_lines=10, sleep_time=0.1):
            self.ct = 0
            self.sleep_time = sleep_time
            self.limit_lines = limit_lines

        def readline(self, n=0):
            if self.ct >= self.limit_lines:
                return ''
            time.sleep(self.sleep_time)
            self.ct += 1
            return 'ping'

    def __init__(self, limit_lines=10, sleep_time=0.1):
        self.pid = 1
        self.stdout = self.MockStdOut(limit_lines, sleep_time)

    def kill(self):
        return

    def wait(self):
        return
