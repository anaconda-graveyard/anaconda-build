"""
Write IO back to build log on the binstar server
"""
from __future__ import print_function, unicode_literals, absolute_import

import base64
import codecs
import functools
import io
import json
import logging

import requests
from binstar_client import BinstarError

log = logging.getLogger('binstar.build')

# write to the servers when more than BUF_SIZE of data has been buffered
BUF_SIZE = 72 # bytes
METADATA_PREFIX = b'anaconda-build-metadata:'
# number of write attempts to make before giving up
MAX_WRITE_ATTEMPTS = 5

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


def wrap_file(fd):
    '''
    Wraps a file descriptor such that readline() only blocks until the first `\r` or `\n`

    Args:
        fd: The file descriptor to wrap

    Returns:
        a text-based file-like object
    '''
    fd = fd if isinstance(fd, io.IOBase) else io.open(fd.fileno(), 'rb', buffering=0, closefd=False)
    fd = io.BufferedReader(fd)
    fd = io.TextIOWrapper(fd, encoding='utf-8', errors='replace', newline='')
    return fd


class BuildLog(object):
    """
    This IO object writes data build log output to the
    anaconda server and also to a file.
    """

    INTERVAL = 10  # Send logs to server every `INTERVAL` seconds
    def __init__(self, bs, username, queue, worker_id,
                 job_id, filename=None, quiet=False):

        self.bs = bs
        self.username = username
        self.queue = queue
        self.worker_id = worker_id
        self.job_id = job_id
        self.quiet = quiet

        self.terminate_build = False
        self.metadata = {'section': 'dequeue_build'}
        self.write_to_server = functools.partial(self.bs.log_build_output_structured,
                                                 self.username,
                                                 self.queue,
                                                 self.worker_id,
                                                 self.job_id)
        # the number of consecutive write failures - when this exceeds
        # MAX_WRITE_ATTEMPTS, terminate the build
        self.write_failures = 0

        self.buf = io.BytesIO()

        log.info("Writing build log to %s", filename)
        self.fd = codecs.open(filename, 'wb', buffering=0)

    def terminated(self):
        return self.terminate_build

    def update_metadata(self, metadata):
        self.metadata.update(metadata)
        if 'section' in metadata:
            log.info('Started section %s', metadata['section'])

    def detect_metadata(self, msg):
        # TODO: this call is duplicated in decode_metadata... but exceptions
        # are slow... right?
        if msg.startswith(METADATA_PREFIX):
            try:
                return decode_metadata(msg)
            except (ValueError, TypeError):
                return None

    def writelines(self, lines):
        for line in lines:
            self.writeline(line)

    def writeline(self, line):
        n = len(line)

        metadata = self.detect_metadata(line)
        if metadata:
            self.flush()
            self.update_metadata(metadata)
            log.info('Consumed %s bytes of build output metadata', n)
            return n

        if self.quiet and line.endswith(b'\r'):
            log.info('Quiet: ignored %s bytes of output', )
            return n

        self.buf.write(line)
        if self.buf.tell() >= BUF_SIZE:
            self.flush()

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
        self.flush()
        self.buf.close()
        self.fd.close()
        return

    def flush(self):
        self.buf.truncate()
        msg = self.buf.getvalue()

        if not msg:
            # don't send empty messages to the server
            self.buf.seek(0)
            return

        terminate_build = False
        try:
            self.fd.write(msg)
            self.fd.flush()
            terminate_build = self.write_to_server(msg, self.metadata)
        except (BinstarError, requests.HTTPError, requests.ConnectionError):
            self.write_failures += 1
            log.warn('Failed to write log to server, %s attempts remaining', MAX_WRITE_ATTEMPTS - self.write_failures)

            if self.write_failures >= MAX_WRITE_ATTEMPTS:
                terminate_build = True
                log.error('Failed to write log to server %s times in a row, terminating build', self.write_failures)
        else:
            # we have successfully written this data, remove from the buffer
            self.buf.seek(0)
            # reset consecutive failures
            self.write_failures = 0

        log.info('Wrote %s bytes of build output to anaconda-server', len(msg))

        self.terminate_build = terminate_build
        if terminate_build:
            log.info('anaconda-server responded that the build should be terminated')

