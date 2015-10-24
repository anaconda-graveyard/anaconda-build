from __future__ import print_function
from gevent.monkey import patch_all; patch_all()
# the above line must always come first!
# currently this module cannot be part of the
# binstar-build package because of the patch_all()
# breaking the existing use of threading.
import subprocess as sp
import gevent
import time
import io
import sys
from contextlib import contextmanager


class read_with_timeout:
    """
    This is a class to read the stdout stream from a Popen object

    This will call a callback on every line of output.
    """
    def __init__(self, p0, iotimeout=60, timeout=60*60):
        self.p0 = p0
        self.iotimeout = iotimeout
        self.timeout = timeout


        self.start_time = time.time()
        self.last_read_time = time.time()

        gevent.spawn(self.read)
        gevent.spawn(self.check_timeouts)

    def __call__(self, callback):
        self.callback = callback
        return self

    def read(self):
        while self.p0.poll() is None:

            line = self.p0.stdout.readline()

            if not line:
                print("exiting read loop because line is empty")
                return

            self.last_read_time = time.time()
            self.callback(line)

    def check_timeouts(self):

        while self.p0.poll() is None:

            now = time.time()
            if (now - self.last_read_time) > self.iotimeout:
                self.callback(None, iotimeout=True)

            if (now - self.start_time) > self.timeout:
                self.callback(None, timeout=True)

            time.sleep(1)


@contextmanager
def flush_every(stream, seconds=2):
    '''
    This class flushes the a buffered output every x seconds

    This is so the build log is updated in a timly fasion
    '''
    greenlet = gevent.spawn(_flush_every, stream, seconds=seconds)
    yield
    greenlet.kill()
    stream.flush()

def _flush_every(stream, seconds):
    print("_flush_every", seconds)
    while not stream.closed:
        print("flush because of time")
        stream.flush()
        time.sleep(seconds)

class FakeBuildLog(object):
    """
    This class should actually post to anaconda-server

    but here it is just to show the output.
    """
    def __init__(self):
        self.buffer = io.BytesIO()
        self.closed = False

    def writable(self):
        return True

    def getvalue(self):
        return self.buffer.getvalue()

    def write(self, data):
        print("write to woof")
        self.buffer.write(b'--\n')
        n = self.buffer.write(data)
        self.buffer.write(b'--\n')
        return n

def main(popen_args, timeout, iotimeout):
    stream = FakeBuildLog()
    # Wrap the build log in a BufferedWriter so url requests don't get sent for every line
    # of output
    b_output = io.BufferedWriter(stream)

    p0 = sp.Popen(popen_args, shell=True, stdout=sp.PIPE)

    @read_with_timeout(p0, timeout=timeout, iotimeout=iotimeout)
    def write_line(line, iotimeout=False, timeout=False):
        """
        This should handle any output and the timeout.
        """
        if iotimeout or timeout:
            print("p0.kill()")
            b_output.write(b" | p0.kill()\n")
            if iotimeout:
                b_output.write(b" | iotimeout\n")
            if timeout:
                b_output.write(b" | timeout\n")
            b_output.flush()
            p0.kill()
            return

        b_output.write(line)
        print("line:", line)

    with flush_every(b_output, seconds=2):
        p0.wait()

    print("done!")

    print("-- b_output --")
    out = stream.getvalue().decode()
    print(out)
    return out

if __name__ == "__main__":
    main()
