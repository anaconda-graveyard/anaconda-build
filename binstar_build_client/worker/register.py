from __future__ import print_function, unicode_literals, division, absolute_import

import logging
import os
import platform
import re

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
        worker_id_to_name = WorkerConfiguration.backwards_compat_lookup()
        self.name = worker_id_to_name.get(worker_id, None) or name
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
            "name": getattr(self, 'name', self.worker_id),
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
    def validate_worker_name(cls, bs, name):
        workers_by_name = {}
        for worker in cls.registered_workers(bs):
            if not worker.name in workers_by_name:
                workers_by_name[worker.name] = [worker]
            else:
                workers_by_name[worker.name].append(worker)
        workers = workers_by_name.get(name, [])
        if len(workers) > 1:
            msg = ''
            for worker in workers:
                worker.name = name
                msg += '{name}, id:{worker_id}, hostname:{hostname}, queue:{username}/{queue}\n'.format(**worker.to_dict())
            raise errors.BinstarError('Cannot anaconda worker run {}'
                                      ' (the name is ambiguous).  Use'
                                      ' one of the worker id\'s below'
                                      ' instead.\n\n' + msg)
    @classmethod
    def registered_workers(cls, bs):
        "Iterate over the registered workers on this machine"

        build_query = bs.build_queues(username=None)
        for build_info in build_query:
            queue_name, workers = build_info['_id'], build_info.get('workers', None)
            if not workers:
                continue
            try:
                user, queue = split_queue_arg(queue_name)
            except Exception as e:
                raise ValueError(repr(queue_name))
            for worker in workers:
                try:
                    worker = cls(name=worker.get('name', worker['id']),
                                 worker_id=worker['id'],
                                 username=user,
                                 queue=queue,
                                 platform=worker['platform'],
                                 hostname=worker['hostname'],
                                 dist=worker['dist'])
                    yield worker

                except Exception as e:
                    print('Failed with', repr(e))
                    raise

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
    def load(cls, worker_name, bs, warn=False):

        'Load a worker config from a worker_id'
        for worker in cls.registered_workers(bs):
            if worker_name in (worker.worker_id, worker.name):
                return worker

        raise errors.BinstarError('Worker with id '
                                  '{} not found'.format(worker_name))

    @classmethod
    def register(cls, bs, username, queue, platform, hostname, dist, name=None):
        '''
        Register the worker with anaconda server
        '''
        for worker in cls.registered_workers(bs):
            if name in (worker.name, worker.worker_id):
                raise errors.BinstarError('Cannot have duplicate worker '
                                          '--name or id: {}'.format(name))
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

    @classmethod
    def backwards_compat_lookup(cls):
        '''Also recognize worker --name's from older
        worker configuration files in ~/.workers that
        look like:

        $ cat  ~/.workers/ps_abc1
        dist: darwin10.10
        hostname: 0178-psteinberg.local
        platform: osx-64
        queue: abc
        username: psteinberg
        worker_id: 5697f3320eafa954fc21a3a5

        where ps_abc1 is a --name for a worker registration.

        Returns a dictionary of worker name to worker id from
        these files, if any.

        '''

        worker_id_to_name = {}
        if os.path.exists(cls.REGISTERED_WORKERS_DIR):
            possible_names = os.listdir(cls.REGISTERED_WORKERS_DIR)
            for name in possible_names:
                worker_file = os.path.join(cls.REGISTERED_WORKERS_DIR, name)
                parts = worker_file.split('.')
                if len(parts) > 1:
                    if re.search('^\d+$', parts[-1]):
                        continue # it is a PID file not config
                with open(worker_file, 'r') as f:
                    try:
                        config = yaml.safe_load(f.read())
                    except:
                        log.info('Removing non-yaml file {}'
                                 'from worker pid dir: '
                                 '{}'.format(worker_file,
                                             cls.REGISTERED_WORKERS_DIR))
                        os.unlink(worker_file)
                        config = {}
                if hasattr(config, 'get') and config.get('worker_id', None):
                    if name != config['worker_id']:
                        worker_id_to_name[config['worker_id']] = name

        return worker_id_to_name


