from __future__ import print_function, unicode_literals, division, absolute_import

import logging
import os

from binstar_client import errors
import yaml
from glob import glob
import io


log = logging.getLogger("binstar.build")


def pid_is_running(pid):
    'Return true if the pid is running'
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == 3:
            return False
        raise
    return True


class WorkerConfiguration(object):
    REGISTERED_WORKERS_DIR = os.path.join(os.path.expanduser('~'), '.workers')

    def __init__(self, worker_id, username, queue, platform, hostname, dist):
        self.worker_id = worker_id
        self.username = username
        self.queue = queue
        self.platform = platform
        self.hostname = hostname
        self.dist = dist

    def __str__(self):
        stream = io.StringIO()
        print("<WorkerConfiguration pid={}".format(self.pid), file=stream)
        for key, value in sorted(self.to_dict().items()):
            print("  {}='{}'".format(key, value), file=stream)

        print(">", file=stream)

        return stream.getvalue()

    def __repr__(self):
        return "WorkerConfiguration({})".format(', '.join(self.to_dict().values()))

    def to_dict(self):
        return {
            "worker_id": self.worker_id,
            "username": self.username,
            "queue": self.queue,
            "platform": self.platform,
            "hostname": self.hostname,
            "dist": self.dist,
        }

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False

        return self.to_dict() == other.to_dict()

    @classmethod
    def registered_workers(cls):
        "Iterate over the registered workers on this machine"

        log.info('Registered workers:\n')
        for worker_id in os.listdir(cls.REGISTERED_WORKERS_DIR):
            yield cls.load(worker_id)

    @property
    def filename(self):
        'Filename for to load/save worker config'
        return os.path.join(self.REGISTERED_WORKERS_DIR, self.worker_id)

    @property
    def pid(self):
        for fn in glob(self.filename + '.*'):

            try:
                pid = int(fn.rsplit('.', 1)[-1])
            except ValueError:
                os.unlink(fn)

            if pid_is_running(pid):
                return pid
            else:
                os.unlink(fn)

        return None

    def is_running(self):
        'Test if this worker is running'
        return self.pid is not None

    def set_as_running(self):
        'Flag this worker id as running'
        dst = '{}.{}'.format(self.filename, os.getpid())
        os.link(self.filename, dst)

    @classmethod
    def load(cls, worker_id):
        'Load a worker config from a worker_id'

        worker_file = os.path.join(cls.REGISTERED_WORKERS_DIR, worker_id)

        with open(worker_file) as fd:
            attrs = yaml.safe_load(fd)

        return cls(**attrs)

    @classmethod
    def print_registered_workers(cls):

        log.info('Registered workers:\n')
        has_workers = False
        for f in os.listdir(cls.REGISTERED_WORKERS_DIR):
            worker_file = os.path.join(cls.REGISTERED_WORKERS_DIR, f)
            with open(worker_file, 'r') as fil:
                try:
                    worker = yaml.load(fil.read())
                    has_workers = True
                    log.info('worker-id\t{}\tqueue\t{}/{}'.format(worker['worker_id'], worker['username'], worker['queue']))
                except Exception:
                    log.info('Skipping file worker config file: {} that could ' + \
                             'not be yaml.load\'ed'.format(worker_file))
        if not has_workers:
            log.info('(No registered workers)')

    @classmethod
    def register(cls, bs, username, queue, platform, hostname, dist):
        '''
        Register the worker with anaconda server
        '''

        worker_id = bs.register_worker(username, queue, platform, hostname, dist)
        log.info('Registered worker with worker_id:\t{}'.format(worker_id))

        return WorkerConfiguration(worker_id, username, queue, platform, hostname, dist)

    def save(self):
        'Store worker config in yaml file'

        if not os.path.exists(self.REGISTERED_WORKERS_DIR):
            os.mkdir(self.REGISTERED_WORKERS_DIR)

        with open(self.filename, 'w') as fd:
            yaml.safe_dump(self.to_dict(), fd, default_flow_style=False)

        log.info('Worker config saved at {}.'.format(self.filename))
        log.info('Now run:\n\tanaconda build worker {}'.format(self.worker_id))

    def deregister(self, bs):
        'Deregister the worker from anaconda server'

        try:

            removed_worker = bs.remove_worker(self.username, self.queue, self.worker_id)

            if not removed_worker:
                info = (self.worker_id, self.username, self.queue,)
                raise errors.BinstarError('Failed to remove_worker with argument of ' + \
                                          'worker_id\t{}\tqueue\t{}/{}'.format(*info))

            log.info('Deregistered worker with worker-id {}'.format(self.worker_id))
            os.unlink(self.filename)
            log.debug("Removed worker config {}".format(self.filename))

        except Exception:

            log.info('Failed on anaconda build deregister.\n')
            self.print_registered_workers()
            log.info('deregister failed with error:\n')
            raise

