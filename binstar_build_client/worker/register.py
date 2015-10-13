from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import Namespace
import os
import yaml
import logging

from binstar_client import errors
from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.build_commands.queue import show_queues

log = logging.getLogger("binstar.build")

REGISTERED_WORKERS_DIR = os.path.join(os.path.expanduser('~'), '.workers')

if not os.path.exists(REGISTERED_WORKERS_DIR):
    os.mkdir(REGISTERED_WORKERS_DIR)

class Registration(object):
    fields = ['worker_id',
              'queue',
              'username',
              'platform',
              'hostname',
              'dist',
              'cwd',
              'timeout',
              'is_running',
              ]
    def __init__(self, args):
        for field in self.fields:
            if type(args) == Namespace:
                val = getattr(args, field, None)
            else:
                val = args.get(field, None)
            setattr(self, field, val)

    @property
    def worker_yaml_file(self):
        return os.path.join(REGISTERED_WORKERS_DIR, self.worker_id)

    def save(self):
        worker_dict = {f: getattr(self, f, None) for f in self.fields}
        with open(self.worker_yaml_file, 'w') as f:
            f.write(yaml.dump(worker_dict))

    @classmethod
    def load(cls, bs, worker_id):
        filename = os.path.join(REGISTERED_WORKERS_DIR, worker_id)
        if not os.path.exists(filename):
            if os.path.exists(worker_id):
                # perhaps a path to a config was given instead of worker-id
                filename = worker_id
            else:
                msg = Registration.follow_up_on_worker_id(bs, worker_id)
                raise errors.BinstarError(msg)
        try:
            with open(filename, 'r') as f:
                worker_dict = yaml.load(f.read())
                return Registration(worker_dict)
        except Exception as e:
            msg = Registration.follow_up_on_worker_id(bs, worker_id)
            raise errors.BinstarError(msg)

    @classmethod
    def follow_up_on_worker_id(cls, bs, worker_id):
        found_it = False
        for queue in bs.build_queues(None):
            for worker in queue.get('workers', []):
                if worker['id']  == worker_id:
                    return ('The worker_id {} is registered, '
                           'but not from this machine.').format(worker_id)
        return 'worker_id {} is not a valid worker_id.'.format(worker_id)

    def remove(self):
        os.unlink(self.worker_yaml_file)
        log.debug("Removed worker config {}".format(self.worker_yaml_file))

    def clean_workers_dir(self, bs):
        found_worker_ids = os.listdir(REGISTERED_WORKERS_DIR)
        for queue in bs.build_queues(self.username):
            for worker in queue.get('workers', []):
                if worker['id'] in found_worker_ids:
                    found_worker_ids.pop(found_worker_ids.index(worker['id']))
        for old_file in found_worker_ids:
            path = os.path.join(REGISTERED_WORKERS_DIR, old_file)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.unlink(path)
    def assert_is_not_running(self, bs):
        is_valid = False
        possibly_running = True
        for queue in bs.build_queues(self.username):
            for worker in queue.get('workers', []):
                is_valid = worker['id'] == self.worker_id
                if is_valid and worker['last_seen'] == 'never':
                    possibly_running = False
                if is_valid:
                    break
        if not is_valid:
            raise errors.BinstarError('Worker-id {} is not registered.'.format(self.worker_id))
        if self.is_running and possibly_running:
            raise errors.BinstarError('Worker with id {} is already running.'.format(self.worker_id))


def split_queue_arg(queue):
    if queue.count('/') == 1:
        username, queue = queue.split('/', 1)
    elif queue.count('-') == 2:
        _, username, queue = queue.split('-', 2)
    else:
        raise errors.UserError("Build queue must be of the form build-USERNAME-QUEUENAME or USERNAME/QUEUENAME")
    return username, queue


def register_worker(bs, args, context="worker"):
    '''
    Register the worker with anaconda
    '''
    worker_id = bs.register_worker(args.username, args.queue, args.platform,
                                        args.hostname, args.dist)
    log.info('Registered worker with worker_id:\t{}'.format(worker_id))
    args.worker_id = worker_id
    registration = Registration(args)
    registration.save()
    log.info('Worker config saved at {}.'.format(registration.worker_yaml_file))
    info = (context, context, worker_id)
    log.info('To start the {}, do:\n\tanaconda {} run {}'.format(*info))
    registration.clean_workers_dir(bs)
    return args

def register_worker_main(args, context="worker"):
    if not args.queue:
        raise errors.BinstarError('Argument --queue <USERNAME>/<QUEUE> is required.')
    args.username, args.queue = split_queue_arg(args.queue)
    bs = get_binstar(args, cls=BinstarBuildAPI)
    return register_worker(bs, args, context=context)

def deregister_worker(bs, args, context="worker"):
    ''' Deregister the worker with anaconda'''
    try:
        reg = Registration.load(bs, args.worker_id)
        removed_worker = bs.remove_worker(reg.username, reg.queue, reg.worker_id)
        if not removed_worker:
            info = (context, reg.worker_id, reg.username, reg.queue,)
            raise errors.BinstarError('Failed to remove {} with argument of ' + \
                                      'worker_id\t{}\tqueue\t{}/{}'.format(*info))
        show_registration_info(bs, args)
        log.info('Deregistered {} with worker-id {}'.format(context, reg.worker_id))
        reg.remove()
        reg.clean_workers_dir(bs)
        return args

    except Exception:
        log.info('Failed on anaconda {} deregister.\n'.format(context))
        show_registration_info(bs, args)
        log.info('deregister failed with error:\n')
        raise

def deregister_worker_main(args, context="worker"):
    bs = get_binstar(args, cls=BinstarBuildAPI)
    return deregister_worker(bs, args, context=context)

def print_worker_summary(reg, args):
    log.info('Starting worker:')
    log.info('Hostname: {}'.format(reg.hostname))
    log.info('User: {}'.format(reg.username))
    log.info('Queue: {}'.format(reg.queue))
    log.info('Platform: {}'.format(reg.platform))
    log.info('Worker-id: {}'.format(reg.worker_id))
    log.info('Build Options:')
    log.info('--conda-build-dir: {}'.format(args.conda_build_dir))
    log.info('--show-new-procs: {}'.format(args.show_new_procs))
    log.info('--status-file: {}'.format(args.status_file))
    log.info('--push-back: {}'.format(args.push_back))
    log.info('--one: {}'.format(args.one))
    log.info('--dist: {}'.format(reg.dist))
    log.info('--cwd: {}'.format(reg.cwd))
    log.info('--max-job-duration: {} (seconds)'.format(reg.timeout))


def show_registration_info(bs, args):
    print('Queues and registered workers:')
    show_queues(bs, None)
    running_workers = []
    for queue in bs.build_queues(getattr(args, 'username', None)):
        for worker in queue.get('workers', []):
            reg = Registration.load(bs, worker['id'])
            if reg.is_running:
                running_workers.append((worker['id'], worker['hostname'],
                                        worker['last_seen'],queue['_id']))
    print('Currently running workers registered from this machine:')
    if not running_workers:
        print(' + There are no running workers')
    else:
        for worker, hostname, last_seen, queue in running_workers:
            print(' + worker-id: {}'.format(worker))
            print('         --hostname: {}'.format(hostname))
            print('         --queue: {}'.format(queue))
            print('         --last-seen: {}'.format(last_seen))
