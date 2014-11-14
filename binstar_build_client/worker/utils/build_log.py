"""
Write IO back to build log on the binstar server
"""
import logging
import sys
from threading import Lock, Thread, Event
import traceback

from binstar_client import errors

from requests import ConnectionError

log = logging.getLogger(__name__)

class BuildLog(object):
    """
    This IO object writes data build log output to the binstar server and also to stdout
    
    This object first writes to a buffer that is sent to the server every BuildLog.INTERVAL 
    seconds
    """

    INTERVAL = 4

    def __init__(self, bs, username, queue, worker_id, job_id):
        self.bs = bs
        self.username = username
        self.queue = queue
        self.worker_id = worker_id
        self.job_id = job_id
        self._buffer = ''
        self._write_lock = Lock()
        self._running = False
        self.event = Event()


    def write(self, msg):
        """
        Write to server and also stdout
        
        The if the io thread is running, msg will be appended an internal message buffer
        """
        n = sys.stdout.write(msg)

        if self._running:
            with self._write_lock:
                self._buffer += msg
        else:
            terminate_build = self.bs.log_build_output(self.username, self.queue, self.worker_id, self.job_id, msg)
            self.terminate_build = terminate_build
        return n

    def __enter__(self):
        """
        Start a thread that will post to the server 
        """
        self._running = True
        self._io_thread = Thread(target=self._io_loop, name='io_loop')
        self._io_thread.start()
        self.terminate_build = False
        return self

    def __exit__(self, *args):

        if args[0] is not None:
            self.write("Build Error: An unhandled exception occurred in the build worker")
            self.write('---\n' + ''.join(traceback.format_exception(*args)) + '\n---')

        self._running = False
        self.event.set()
        self._io_thread.join()

    def flush(self):
        """
        Flush the current buffer to the server 
        """
        with self._write_lock:
            msg = self._buffer
            self._buffer = ''

        if not msg:
            return

        try:
            terminate_build = self.bs.log_build_output(self.username, self.queue, self.worker_id, self.job_id, msg)
            self.terminate_build = terminate_build
        except Exception as err:
            log.exception(err)
            # Insert data back to buffer for next write attempt
            with self._write_lock:
                self._buffer = msg + self._buffer


    def _io_loop(self):
        """
        Loop to write buffer to server 
        every self.INTERVAL seconds
        """
        while self._running:
            self.flush()
            self.event.wait(self.INTERVAL)

        self.flush()






