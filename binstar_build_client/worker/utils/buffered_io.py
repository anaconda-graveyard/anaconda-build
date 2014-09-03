"""
Popen module with buffered IO 

i.e. stdout, stderr can be any file 'like' object. Like an io.BytesIO() object

Also this adds a new keyword argument iotimeout which will terminate the process if no output is recieved for 
iotimeout seconds  
"""

from __future__ import print_function

import  os
from subprocess import Popen, STDOUT
from threading import Thread
import time
import psutil

import logging
log = logging.getLogger(__name__)

class BufferedPopen(Popen):
    def __init__(self, args, stdout=None, iotimeout=None, **kwargs):

        self._iotimeout = iotimeout

        if stdout is not None:
            r, w = os.pipe()
            self._rfile = os.fdopen(r)
            self._wfile = os.fdopen(w, 'w')
            self._output = stdout
            self._last_io = time.time()
        else:
            self._wfile = None

        Popen.__init__(self, args, stdout=self._wfile, stderr=STDOUT, **kwargs)

        self._timeout_thread = None
        self._io_thread = None

        if stdout is not None:
            self._io_thread = Thread(target=self._io_loop, name='io_loop')
            self._io_thread.start()

            if self._iotimeout:
                self._timeout_thread = Thread(target=self._io_timeout_loop, name='io_timeout_loop')
                self._timeout_thread.start()

    def wait(self):
        returncode = Popen.wait(self)
        log.debug("returncode", returncode)

        if self._wfile is not None:
            log.debug("close wfile")
            self._wfile.close()

        if self._io_thread and self._io_thread.is_alive():
            log.debug("self._io_thread.join()")
            self._io_thread.join()
        if self._timeout_thread and self._timeout_thread.is_alive():
            log.debug("self._timeout_thread.join()")
            self._timeout_thread.join()

        return returncode

    def _io_timeout_loop(self):
        while self.poll() is None:
            elapsed = time.time() - self._last_io

            if elapsed > self._iotimeout:
                log.debug("term proc")
                self._output.write("\nTimeout: No output from program for %s seconds\n" % self._iotimeout)
                self._output.write("\nTimeout: If you require a longer timeout you "
                          "may set the 'iotimeout' variable in your .binstar.yml file\n")
                self._output.write("[Terminating]\n")

                # self.send_signal(signal.SIGKILL)

                parent = psutil.Process(self.pid)
                for child in parent.get_children(recursive=True):
                    child.kill()
                parent.kill()
                time.sleep(.1)
                break

            if elapsed > 0:
                sleep_for = min(self._iotimeout, elapsed)
            else:
                sleep_for = self._iotimeout

            time.sleep(sleep_for)

        log.debug("exit Timeout Loop")

    def _io_loop(self):
        while self.poll() is None:
            log.debug("readline...")
            data = self._rfile.readline()
            log.debug("done readline")
            self._last_io = time.time()
            self._output.write(data)
        log.debug("exit IO Loop")
        self._rfile.close()


