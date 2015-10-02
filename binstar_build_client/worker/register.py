from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import yaml
import logging

from binstar_client import errors
log = logging.getLogger("binstar.build")

REGISTERED_WORKERS_DIR = os.path.join(os.path.expanduser('~'), '.workers')

if not os.path.exists(REGISTERED_WORKERS_DIR):
    os.mkdir(REGISTERED_WORKERS_DIR)

def print_registered_workers():
    log.info('Registered workers:\n')   
    has_workers = False 
    for f in os.listdir(REGISTERED_WORKERS_DIR):
        worker_file = os.path.join(REGISTERED_WORKERS_DIR, f)
        with open(worker_file, 'r') as fil:
            try:
                worker = yaml.load(fil.read())
                has_workers = True
                log.info('worker-id\t{}\tqueue\t{}/{}'.format(worker['worker_id'], worker['username'], worker['queue']))
            except Exception:
                log.info('Skipping file worker config file: {} that could ' +\
                         'not be yaml.load\'ed'.format(worker_file))
    if not has_workers:
        log.info('(No registered workers)')

def register_worker(bs, args):
    '''
    Register the worker with anaconda
    '''
    worker_id = bs.register_worker(args.username, args.queue, args.platform,
                                        args.hostname, args.dist)
    log.info('Registered worker with worker_id:\t{}'.format(worker_id))
    args.worker_id = worker_id
    filename = os.path.join(REGISTERED_WORKERS_DIR, args.worker_id)
    with open(filename, 'w') as fd:
        yaml.dump(vars(args), fd)
    log.info('Worker config saved at {}.'.format(filename))
    log.info('Now run:\n\tanaconda build worker {}'.format(worker_id))
    return args

def deregister_worker(bs, args):
    ''' Deregister the worker with anaconda'''
    try:
        filename = os.path.join(REGISTERED_WORKERS_DIR, args.worker_id)
        if not os.path.exists(filename):
            raise errors.BinstarError('Cannot find {}.  Perhaps the worker was already removed.'.format(filename))
        with open(filename, 'r') as fil:
            vars(args).update(yaml.load(fil.read()))
        removed_worker = bs.remove_worker(args.username, args.queue, args.worker_id)
        if not removed_worker:
            info = (args.worker_id, args.username, args.queue,)
            raise errors.BinstarError('Failed to remove_worker with argument of ' + \
                                      'worker_id\t{}\tqueue\t{}/{}'.format(*info))
        log.info('Deregistered worker with worker-id {}'.format(args.worker_id))
        os.unlink(filename)
        log.debug("Removed worker config {}".format(filename))
        return args
    except Exception:
        log.info('Failed on anaconda build deregister.\n')
        print_registered_workers()
        log.info('deregister failed with error:\n')
        raise