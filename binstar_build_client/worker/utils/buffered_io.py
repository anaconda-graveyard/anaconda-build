"""
Popen module with buffered IO 

i.e. stdout, stderr can be any file 'like' object. Like an io.BytesIO() object

Also this adds a new keyword argument iotimeout which will terminate the process if no output is recieved for 
iotimeout seconds  
"""

from __future__ import print_function

import logging
from subprocess import Popen, STDOUT, PIPE
import psutil
from binstar_build_client.worker.utils.streamio import IOStream



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
    def __init__(self, args, stdout=None, iotimeout=None, timeout=None, **kwargs):
        self._output = stdout

        Popen.__init__(self, args, stdout=PIPE, stderr=STDOUT,
                       **kwargs)

        self._iostream = IOStream(self.stdout, self._output, iotimeout, timeout, self.timeout_callback)
        self._iostream.start()

    def wait(self):
        """Wait for child process to terminate.  Returns returncode
        attribute.
        
        If timeout is given, the process will be killed after timeout seconds if it is not finished 
        """
        returncode = Popen.wait(self)

#         self._finished_event.set()
        log.debug("returncode", returncode)

        if self._iostream.is_alive():
            log.debug("self._io_thread.join()")
            self._iostream.join()

        return returncode

    def timeout_callback(self, reason='iotimeout'):

        log.debug("timeout_callback")

        if reason == 'iotimeout':
            self._output.write("\nTimeout: No output from program for %s seconds\n" % self._iostream.iotimeout)
            self._output.write("\nTimeout: If you require a longer timeout you "
                      "may set the 'iotimeout' variable in your .binstar.yml file\n")
            self._output.write("[Terminating]\n")
        elif reason == 'timeout':
            self._output.write("\nTimeout: build exceeded maximum build time of %s seconds\n" % self._iostream.timeout)
            self._output.write("[Terminating]\n")
        else:
            self._output.write("\nTerminate: User requested build to be terminated\n")
            self._output.write("[Terminating]\n")

        self.kill_tree()

    def kill_tree(self):
        'Kill all processes and child processes'
        try:
            log.warn("Kill Tree parent pid:%s" % self.pid)
            parent = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            log.warn("Parent pid %s is already dead" % self.pid)
            # Already dead
            return

        children = parent.get_children(recursive=True)

        self.kill()
        for child in children:
            if child.is_running():
                log.warn(" - Kill child pid %s" % child.pid)
                child.kill()

