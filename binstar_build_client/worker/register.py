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

def split_queue_arg(queue):
    '''
    Support old and new style queue
    '''

    if queue.count('/') == 1:
        username, queue = queue.split('/', 1)
    elif queue.count('-') == 2:
        _, username, queue = queue.split('-', 2)
    elif queue.count('/') == 2:
        _, username, queue = queue.split('/', 2)
    else:
        raise errors.UserError(
            "Build queue must be of the form "
            "build-USERNAME-QUEUENAME or USERNAME/QUEUENAME"
        )

    return username, queue


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
    HOSTNAME = platform.node()
    def __init__(self, name, worker_id, username, queue, platform, hostname, dist):
        self.name = name
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
    def registered_workers(cls, bs):
        "Iterate over the registered workers on this machine"
        username = bs.user()['login']
        build_query = bs.build_queues(username=username)
        for build_info in build_query:
            queue_name, workers = build_info['_id'], build_info.get('workers', None)
            if not workers:
                continue
            try:
                user, queue = split_queue_arg(queue_name)
            except Exception as e:
                raise ValueError(repr(queue_name))
            for worker in workers:
                if worker['hostname'] != cls.HOSTNAME:
                    continue
                try:
                    yield cls(name=worker.get('name', worker['id']),
                              worker_id=worker['id'],
                              username=user,
                              queue=queue,
                              platform=worker['platform'],
                              hostname=worker['hostname'],
                              dist=worker['dist'])
                except Exception as e:
                    print('Failed on', kwargs, 'with', repr(e))

    @property
    def filename(self):
        'Filename for to load/save worker config'
        return os.path.join(self.REGISTERED_WORKERS_DIR, self.name)


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
    def load(cls, worker_name, bs):

        'Load a worker config from a worker_id'
        username = bs.user()['login']
        for worker in cls.registered_workers(bs):
            log.info('worker {}'.format(repr(worker)))
            if worker_name == worker.worker_id or worker_name == worker.name:
                if worker.hostname == cls.HOSTNAME:
                    return worker
        raise errors.BinstarError('Worker with id '
                                  '{} not found'.format(worker_name))
    @classmethod
    def print_registered_workers(cls, bs):

        has_workers = False

        log.info('Registered workers:')

        for wconfig in cls.registered_workers(bs):
            has_workers = True

            msg = '{name}, id:{worker_id}, hostname:{hostname}, queue:{username}/{queue}'.format(name=wconfig.name, **wconfig.to_dict())
            if wconfig.pid:
                msg += ' (running with pid: {})'.format(wconfig.pid)

            log.info(msg)

        if not has_workers:
            log.info('(No registered workers)')

    @classmethod
    def register(cls, bs, username, queue, platform, hostname, dist, name=None):
        '''
        Register the worker with anaconda server
        '''
        for worker in cls.registered_workers(bs):
            if worker.name == name:
                raise errors.BinstarError('Cannot have duplicate worker '
                                          '--name from same host: {}'.format(name))
        worker_id = bs.register_worker(username, queue, platform, hostname, dist,name=name)
        log.info('Registered worker with worker_id:\t{}'.format(worker_id))

        if name is None:
            name = worker_id

        return WorkerConfiguration(name, worker_id, username, queue, platform, hostname, dist)


    def deregister(self, bs, as_json=False):
        'Deregister the worker from anaconda server'

        try:

            removed_worker = bs.remove_worker(self.username, self.queue, self.worker_id)

            if not removed_worker:
                raise errors.BinstarError('Failed to remove_worker with argument of ' + \
                                          'worker_id\t{}\tqueue\t{}'.format(self.worker_id, self.queue))

            log.info('Deregistered worker with worker-id {}'.format(self.worker_id))
        except Exception:

            log.info('Failed on anaconda build deregister.\n')
            self.print_registered_workers(bs)
            log.info('deregister failed with error:\n')
            raise

    @classmethod
    def deregister_all(cls, bs):

        for worker in cls.registered_workers(bs):
            worker.deregister(bs)
