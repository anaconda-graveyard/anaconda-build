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

        self.write_to_server = functools.partial(self.bs.log_build_output,
                                                 self.username,
                                                 self.queue,
                                                 self.worker_id,
                                                 self.job_id)


        log.info("Writing build log to %s" % filename)
        if filename:
            self.fd = codecs.open(filename, 'wb')
        else:
            self.fd = None


    def write(self, msg):
        """
        Write to server and also stdout
        
        The if the io thread is running, msg will be appended an internal message buffer
        """
        umsg = msg.encode('utf-8', errors='replace')

        terminate_build = self.write_to_server(umsg)
        self.terminate_build = terminate_build

        n = self.fd.write(msg)
        print('write', n)
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


