from threading import Event, Thread
import time
import logging

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
        self.timout_occurred = False
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
                self.event.set()
                self.timout_occurred = True
                self.callback()
                break

    def __enter__(self):
        self.event.clear()
        self._t = Thread(target=self._loop, name='timeout')
        self._t.start()

        return self

    def __exit__(self, *args):
        self.event.set()
        self._t.join()

def read_with_timeout(p0, output,
                      timeout=60 * 60,
                      iotimeout=60,
                      flush_iterval=10,
                      build_was_stopped_by_user=lambda:None):
    """
    Read the stdout from a Popen object and wait for it to
    """

    @Timeout(timeout)
    def timer():
        log.info("Kill build process || timeout")
        p0.kill()


    @Timeout(iotimeout)
    def iotimer():
        log.info("Kill build process || iotimeout")
        p0.kill()

    with timer, iotimer:
        line = p0.readline()
        last_flush = time.time()

        while line:
            iotimer.tick()

            output.write(line)
            if build_was_stopped_by_user():
                log.info("Kill build process || user requested")
                p0.kill()
                break

            if time.time() - last_flush > flush_iterval:
                last_flush = time.time()
                output.flush()

            # Note: this is a blocking read, for any hanging operations
            # The user will not get any output for  iotimeout seconds
            # when the io timer kills the process
            line = p0.readline()

    while p0.poll() is None:
        log.info("Waiting for build process with pid {} to end".format(p0.pid))
        time.sleep(1)

    p0.wait()

    if timer.timout_occurred:
        output.write("\nTimeout: build exceeded maximum build time of {} seconds\n"
                     .format(timeout).encode(errors='replace'))
        output.write(b"[Terminated]\n")

    if iotimer.timout_occurred:
        output.write("\n\nTimeout: No output from program for {} seconds\n"
                     .format(iotimeout).encode(errors='replace'))
        output.write(b"\nTimeout: If you require a longer timeout you "
                     b"may set the 'iotimeout' variable in your .binstar.yml file\n")
        output.write(b"[Terminated]\n")

    if build_was_stopped_by_user():
        output.write(b"\n\nTerminate: User requested build to be terminated\n")
        output.write(b"[Terminated]\n")

    output.flush()
