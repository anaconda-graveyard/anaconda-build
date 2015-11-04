from __future__ import print_function, unicode_literals, division, absolute_import

import logging
import os
import platform

from binstar_client import errors
import yaml
from glob import glob
import io
from contextlib import contextmanager
import psutil

log = logging.getLogger("binstar.build")


def pid_is_running(pid):
    'Return true if the pid is running'

    try:
        psutil.Process(pid)
        return True
    except psutil.NoSuchProcess:
        return False

class InvalidWorkerConfigFile(errors.BinstarError):
    pass

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
        print("WorkerConfiguration", file=stream)

        print("\tpid: {}".format(self.pid), file=stream)

        for key, value in sorted(self.to_dict().items()):
            print("\t{}: {}".format(key, value), file=stream)

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

        for worker_id in os.listdir(cls.REGISTERED_WORKERS_DIR):
            if '.' not in worker_id:
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

        if self.pid is None:
            return False

        return pid_is_running(self.pid)

    @contextmanager
    def running(self):
        'Flag this worker id as running'

        if self.is_running():
            msg = "This worker appears to already be running with pid {}".format(self.pid)
            raise errors.BinstarError(msg)

        dst = '{}.{}'.format(self.filename, os.getpid())
        try:
            with open(dst, 'w') as out:
                out.write('')
        except (OSError, AttributeError):
            log.warning("Could not link the pid to a pidfile")
        try:
            yield
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)




    @classmethod
    def load(cls, worker_id):
        'Load a worker config from a worker_id'

        worker_file = os.path.join(cls.REGISTERED_WORKERS_DIR, worker_id)
        if not os.path.isfile(worker_file):
            raise errors.BinstarError("Worker with ID {} does not exist locally ({})".format(worker_id, worker_file))

        with open(worker_file) as fd:
            try:
                attrs = yaml.safe_load(fd)
            except yaml.error.YAMLError as err:
                log.error(err)
                raise InvalidWorkerConfigFile("The worker registration file can not be read")

        if not attrs:
            raise InvalidWorkerConfigFile("The worker registration file {} "
                                          "appears to be empty".format(worker_file))

        expected = {'worker_id', 'username', 'queue', 'platform', 'hostname', 'dist'}

        if set(attrs) != expected:
            log.error("Expected the worker registration file to contain the values\n\t"
                      "{}\ngot:\n\t{}".format(', '.join(expected), ' ,'.join(attrs)))
            raise InvalidWorkerConfigFile("The worker registration file {} "
                                          "does not contain the correct values".format(worker_file))

        worker_config = cls(**attrs)


        return worker_config

    @classmethod
    def print_registered_workers(cls):

        has_workers = False

        for wconfig in cls.registered_workers():
            msg = 'id: {worker_id} hostname: {hostname} queue: {username}/{queue}'.format(**wconfig.to_dict())
            if wconfig.pid:
                msg += ' (running with pid: {})'.format(wconfig.pid)

            log.info(msg)

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


    def deregister(self, bs, as_json=False):
        'Deregister the worker from anaconda server'

        try:

            removed_worker = bs.remove_worker(self.username, self.queue, self.worker_id)

            if not removed_worker:
                info = (self.worker_id, self.username, self.queue,)
                raise errors.BinstarError('Failed to remove_worker with argument of ' + \
                                          'worker_id\t{}\tqueue\t{}/{}'.format(*info))

            log.info('Deregistered worker with worker-id {}'.format(self.worker_id))
            os.unlink(self.filename)
            msg = 'Removed worker config file {0}'
            log.info(msg.format(self.filename))
        except Exception:

            log.info('Failed on anaconda build deregister.\n')
            self.print_registered_workers()
            log.info('deregister failed with error:\n')
            raise

    @classmethod
    def deregister_all(cls, bs):

        this_node = platform.node()
        for worker in cls.registered_workers():
            if worker.hostname == this_node:
                worker.deregister(bs)
