"""
Write IO back to build log on the binstar server
"""
from __future__ import print_function, unicode_literals, absolute_import

import base64
import codecs
import functools
import json
import logging


log = logging.getLogger(__name__)

METADATA_PREFIX = b'anaconda-build-metadata:'

def encode_metadata(metadata):
    '''
    Encodes the dictionary *metadata* into something safe to interpolate into a
    script.

    We can't just json.dumps, because the shell might freak out about some
    special characters like $, ' or ^

    Args:
        metadata: (dict)

    Returns:
        (bytes) the encoded metadata
    '''
    payload = base64.urlsafe_b64encode(json.dumps(metadata).encode('ascii'))
    return METADATA_PREFIX + payload


def decode_metadata(metadata_tag):
    '''
    Converts an encoded metadata tag into a dictionary of metadata

    Raises:
        ValueError: not a valid metadata tag

    '''
    if not metadata_tag.startswith(METADATA_PREFIX):
        raise ValueError('Metadata should begin with %r' % METADATA_PREFIX)
    payload = metadata_tag[len(METADATA_PREFIX):]
    return json.loads(base64.urlsafe_b64decode(payload).decode('ascii'))


class BuildLog(object):
    """
    This IO object writes data build log output to the
    anaconda server and also to a file.
    """

    INTERVAL = 10  # Send logs to server every `INTERVAL` seconds
    def __init__(self, bs, username, queue, worker_id,
                 job_id, filename=None, datatags=None):

        self.bs = bs
        self.username = username
        self.queue = queue
        self.worker_id = worker_id
        self.job_id = job_id
        self.terminate_build = False
        self.current_section = 'dequeue_build'
        self.status = None
        self.metadata = {'section': 'dequeue_build'}
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

    def update_metadata(self, metadata):
        self.metadata.update(metadata)
        if 'section' in metadata:
            self.current_section = metadata['section']
            log.info('New section %s', self.current_section)

    def detect_metadata(self, msg):
        # TODO: this call is duplicated in decode_metadata... but exceptions
        # are slow... right?
        if msg.startswith(METADATA_PREFIX):
            try:
                return decode_metadata(msg)
            except ValueError:
                return None

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

        n = len(msg)

        metadata = self.detect_metadata(msg)
        if metadata:
            self.update_metadata(metadata)
            log.info('Consumed {} bytes of build output metadata'.format(n))
            return n

        self.fd.write(msg)

        terminate_build = self.write_to_server(msg, self.metadata)
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

