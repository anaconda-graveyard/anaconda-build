"""
Write IO back to build log on the binstar server
"""
from __future__ import print_function, unicode_literals, absolute_import

import codecs
import functools
import json
import logging


log = logging.getLogger(__name__)

class BuildLog(object):
    """
    This IO object writes data build log output to the
    anaconda server and also to a file.
    """

    INTERVAL = 10  # Send logs to server every `INTERVAL` seconds
    SECTION_TAG = b'anaconda-build-section-tag'
    def __init__(self, bs, username, queue, worker_id,
                 job_id, filename=None, datatags=None):

        self.bs = bs
        self.username = username
        self.queue = queue
        self.worker_id = worker_id
        self.job_id = job_id
        self.terminate_build = False
        self.current_tag = 'start_build_on_worker'
        self.status = ''
        self.datatags = datatags or []
        self.user_data = {}
        self.write_to_server = functools.partial(self.bs.log_build_output_structured,
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

    def detect_tags(self, msg):
        if self.SECTION_TAG in msg:
            self.current_tag = " ".join(msg.split()[1:])
            log.info('Enter {} {}'.format(self.SECTION_TAG.decode(), self.current_tag))
            if self.current_tag.lower().startswith('exiting'):
                self.current_tag, self.status = (_.strip() for _ in self.current_tag.split())
        for tag in self.datatags:
            if msg.startswith(tag):
                content = msg.replace(tag, '').strip()
                try:
                    content = json.loads(content)
                except:
                    pass
                if not tag in self.user_data:
                    self.user_data[tag] = []
                self.user_data[tag].append(content)

    def write(self, msg):
        """
        Write to server and also stdout

        The if the io thread is running, msg will be appended an internal message buffer
        """
        # msg is a memory view object
        if isinstance(msg, memoryview):
            msg = msg.tobytes()

        if not isinstance(msg, bytes):
            raise TypeError("a bytes-like object is required, not {}".format(type(msg)))

        self.fd.write(msg)
        self.detect_tags(msg)
        n = len(msg)

        terminate_build = self.write_to_server(msg, self.current_tag, self.status)
        self.terminate_build = terminate_build

        log.info('Wrote {} bytes of build output to anaconda-server'.format(n))

        if terminate_build:
            log.info('anaconda-server responded that the build should be terminated')

        return n

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

