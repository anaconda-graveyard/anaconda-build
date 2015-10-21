"""
Write IO back to build log on the binstar server
"""
from __future__ import print_function, unicode_literals, absolute_import

import codecs
import functools
import logging


log = logging.getLogger(__name__)

class BuildLog(object):
    """
    This IO object writes data build log output to the
    anaconda server and also to a file.
    """

    INTERVAL = 10  # Send logs to server every `INTERVAL` seconds

    def __init__(self, bs, username, queue, worker_id, job_id, filename=None):

        self.bs = bs
        self.username = username
        self.queue = queue
        self.worker_id = worker_id
        self.job_id = job_id
        self.terminate_build = False

        self.write_to_server = functools.partial(self.bs.log_build_output,
                                                 self.username,
                                                 self.queue,
                                                 self.worker_id,
                                                 self.job_id)


        log.info("Writing build log to %s" % filename)
        if filename:
            self.fd = codecs.open(filename, 'wb', buffering=0)
        else:
            self.fd = None

    def terminated(self):
        return self.terminate_build


    def write(self, msg):
        """
        Write to server and also stdout

        The if the io thread is running, msg will be appended an internal message buffer
        """
        # msg is a memory view object
        if isinstance(msg, memoryview):
            msg = msg.tobytes()
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8', errors='replace')
        terminate_build = self.write_to_server(msg)
        self.terminate_build = terminate_build


        self.fd.write(msg)

        log.info('Wrote {} bytes of build output to anaconda-server'.format(len(msg)))

        if terminate_build:
            log.info('anaconda-server responded that the build should be terminated')

        return len(msg)

    def writable(self):
        return True

    def readable(self):
        return False

    @property
    def closed(self):
        return self.fd.closed

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.fd.close()
        return

    def flush(self):
        self.fd.flush()

