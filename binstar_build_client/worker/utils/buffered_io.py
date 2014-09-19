"""
Popen module with buffered IO 

i.e. stdout, stderr can be any file 'like' object. Like an io.BytesIO() object

Also this adds a new keyword argument iotimeout which will terminate the process if no output is recieved for 
iotimeout seconds  
"""

from __future__ import print_function

import logging
from subprocess import Popen, STDOUT, PIPE
from threading import Thread, Event
import psutil
import time



log = logging.getLogger(__name__)

def is_special(fd):
    """
    Test if a stream argument to POPEN is a subprocess.STDOUT or  subprocess.PIPE etc.
    """

    if fd is None:
        return True
    elif isinstance(fd, int) and fd <= 0:
        return True
    return False

class BufferedPopen(Popen):
    """
    Open a process and Buffer the output to *any* IO object (like `io.BytesIO`)
    """
    def __init__(self, args, stdout=None, iotimeout=None, **kwargs):

        self._iotimeout = iotimeout
        self._last_io = time.time()
        self._finished_event = Event()


        self._output = stdout

        Popen.__init__(self, args, stdout=PIPE, stderr=STDOUT,
                       **kwargs)

        self._timeout_thread = None
        self._io_thread = None

        if not is_special(stdout):
            self._io_thread = Thread(target=self._io_loop, name='io_loop')
            self._io_thread.start()

            if self._iotimeout:
                self._timeout_thread = Thread(target=self._io_timeout_loop, name='io_timeout_loop')
                self._timeout_thread.start()

    def wait(self, timeout=None):
        """Wait for child process to terminate.  Returns returncode
        attribute.
        
        If timeout is given, the process will be killed after timeout seconds if it is not finished 
        """

        if timeout:
            self.kill_after(timeout)

        returncode = Popen.wait(self)

        self._finished_event.set()
        log.debug("returncode", returncode)

        if self._io_thread and self._io_thread.is_alive():
            log.debug("self._io_thread.join()")
            self._io_thread.join()
        if self._timeout_thread and self._timeout_thread.is_alive():
            log.debug("self._timeout_thread.join()")
            self._timeout_thread.join()

        return returncode

    def kill_after(self, timeout):
        self._timeout_thread = Thread(target=self._kill_after, name='kill_after', args=(timeout,))
        self._timeout_thread.start()

    def _kill_after(self, timeout):

        finished = self._finished_event.wait(timeout)
        if not finished:

            log.debug("term proc")
            self._output.write("\nTimeout: build exceeded maximum build time of %s seconds\n" % timeout)
            self._output.write("[Terminating]\n")

            self.kill_tree()

    def _io_timeout_loop(self):
        """
        Loop until Popen.wait exits
        
        If Popen exceeds iotimeout seconds without producing any output, 
        then kill_tree will be called.
        """

        while self.poll() is None:
            elapsed = time.time() - self._last_io

            if elapsed >= self._iotimeout:
                log.debug("term proc")
                self._output.write("\nTimeout: No output from program for %s seconds\n" % self._iotimeout)
                self._output.write("\nTimeout: If you require a longer timeout you "
                          "may set the 'iotimeout' variable in your .binstar.yml file\n")
                self._output.write("[Terminating]\n")

                self.kill_tree()
                break

            elif 1 > elapsed:
                sleep_for = 1
            elif self._iotimeout > elapsed > 0:
                sleep_for = self._iotimeout - elapsed
            else:
                sleep_for = self._iotimeout

            # Sleep if the process is not finished
            self._finished_event.wait(sleep_for)


        log.debug("exit Timeout Loop")

    def kill_tree(self):
        'Kill all processes and child processes'
        parent = psutil.Process(self.pid)
        for child in parent.get_children(recursive=True):
            child.kill()
        parent.kill()

    def _io_loop(self):
        '''Loop over lines of output
        
        This should be run in a thread
        '''

        while self.poll() is None:
            log.debug("readline...")
            data = self.stdout.readline()
            log.debug("done readline")
            self._last_io = time.time()
            self._output.write(data)

        data = self.stdout.read()
        self._output.write(data)
        log.debug("exit IO Loop")


