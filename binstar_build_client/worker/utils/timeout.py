from threading import Event, Thread
import logging
import re
import time

import io

from binstar_build_client.worker.utils.build_log import wrap_file

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
        self.timeout_occurred = False
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
                log.debug("Timer: timeout_occurred")
                self.event.set()
                self.timeout_occurred = True
                self.callback()
                break
        log.debug("Timer: finished")

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
                      flush_interval=10,
                      build_was_stopped_by_user=lambda:None
                      ):
    """
    Read the stdout from a Popen object, writing to output and wait for it to
    """

    # TODO: this function `read_with_timeout` is a bad abstraction.
    # clean it up.
    stdout = wrap_file(p0.stdout)

    @Timeout(timeout)
    def timer():
        log.info("Kill build process || timeout")
        p0.kill()


    @Timeout(iotimeout)
    def iotimer():
        log.info("Kill build process || iotimeout")
        p0.kill()

    log.debug("Starting timers")
    with timer, iotimer:
        last_flush = time.time()

        log.debug("Wait for line ...")
        line = stdout.readline().encode('utf-8')
        log.debug("Got line {}:{!r}".format(len(line), line))

        while line:
            iotimer.tick()

            output.writelines([line])
            if build_was_stopped_by_user():
                log.info("Kill build process || user requested")
                p0.kill()
                break

            if time.time() - last_flush > flush_interval:
                last_flush = time.time()
                log.debug("Flush output")
                output.flush()

            # Note: this is a blocking read, for any hanging operations
            # The user will not get any output for  iotimeout seconds
            # when the io timer kills the process
            log.debug("Wait for line ...")
            line = stdout.readline().encode('utf-8')
            log.debug("Got line {}:{!r}".format(len(line), line))

    while p0.poll() is None:
        log.info("Waiting for build process with pid {} to end".format(p0.pid))
        time.sleep(1)

    log.debug("Waiting for process {} to finish".format(p0.pid))
    p0.wait()

    if timer.timeout_occurred:
        output.writelines([
            b"\n",
            "Timeout: build exceeded maximum build time of {} seconds\n".format(timeout).encode(errors='replace'),
            b"[Terminated]\n",
        ])

    if iotimer.timeout_occurred:
        output.writelines([
            b"\n",
            "Timeout: No output from program for {} seconds\n"
                .format(iotimeout).encode(errors='replace'),
            b"\tIf you require a longer timeout you "
            b"may set the 'iotimeout' variable in your .binstar.yml file\n",
            b"[Terminated]\n",
        ])

    if build_was_stopped_by_user():
        output.writelines([
            b"\n",
            b"\Terminate: User requested build to be terminated\n",
            b"[Terminated]\n",
        ])

    output.flush()
