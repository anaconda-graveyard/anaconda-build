from threading import Event, Thread
import time
import logging
from binstar_build_client.worker.utils.kill_tree import kill_tree

log = logging.getLogger('binstar.build')


class Timeout:
    """
    Timeout context
    
    @timeout()
    def timeout1():
        #do somthing
        
    with timeout1:
        wait()
    """
    def __init__(self, seconds=60 * 60):
        self.seconds = seconds
        self.event = Event()
        self.last_tick = time.time()

    def __call__(self, func):
        self.callback = func
        return self

    def tick(self):
        self.last_tick = time.time()

    def _loop(self):
        while not self.event.wait(1):
            diff_time = time.time() - self.last_tick
            if diff_time > self.seconds:
                self.callback()

    def __enter__(self):

        self._t = Thread(target=self._loop, name='timeout')
        self._t.start()

        return self

    def __exit__(self, *args):
        self.event.set()
        self._t.join()

def read_with_timout(p0, output, timeout=60 * 60, iotimeout=60, flush_iterval=10):
    """
    Read the stdout from a Popen object and wait for it to
    """

    @Timeout(timeout)
    def timer():
        log.info("Kill build process || timeout")
        output.write(b"Kill build process || timeout")
        kill_tree(p0)


    @Timeout(iotimeout)
    def iotimer():
        log.info("Kill build process || iotimeout")
        output.write(b"Kill build process || iotimeout")
        kill_tree(p0)

    with timer, iotimer:

        line = p0.stdout.readline()
        last_flush = time.time()

        while line:
            iotimer.tick()

            output.write(line)

            if time.time() - last_flush > flush_iterval:
                last_flush = time.time()
                output.flush()

            line = p0.stdout.readline()

    p0.wait()
    output.flush()
