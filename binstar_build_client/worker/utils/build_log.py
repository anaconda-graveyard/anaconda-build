"""
Write IO back to build log on the binstar server
"""

import sys
from threading import Lock, Thread, Event

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

        if self._running:
            with self._write_lock:
                self._buffer += msg
        else:
            pass
            self.bs.log_build_output(self.username, self.queue, self.worker_id, self.job_id, msg)

        n = sys.stdout.write(msg)
        return n

    def __enter__(self):
        """
        Start a thread that will post to the server 
        """
        self._running = True
        self._io_thread = Thread(target=self._io_loop, name='io_loop')
        self._io_thread.start()
        return self

    def __exit__(self, *args):

        if args[0] is not None:
            self.write("Build Error: An unhandled exception occurred in the build worker")

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

        self.bs.log_build_output(self.username, self.queue, self.worker_id, self.job_id, msg)

    def _io_loop(self):
        """
        Loop to write buffer to server 
        every self.INTERVAL seconds
        """
        while self._running:
            if self._buffer:
                self.flush()
            else:
                self.event.wait(self.INTERVAL)

        self.flush()






