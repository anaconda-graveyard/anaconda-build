from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import Namespace
import os
import yaml
import logging
import tempfile

from binstar_client import errors
log = logging.getLogger("binstar.build")

REGISTERED_WORKERS_FILE = os.path.join(os.path.expanduser('~'), '.anaconda_workers.yaml')

def print_registered_workers():
    no_workers = "There are no registered workers listed in {} on this machine.".format(REGISTERED_WORKERS_FILE)
    if not os.path.exists(REGISTERED_WORKERS_FILE):
        log.info(no_workers)
        return
    with open(REGISTERED_WORKERS_FILE, 'r') as f:
        registered_workers = yaml.load(f.read())
        if registered_workers:
            log.info('There are {} registered worker(s) from this machine:'.format(len(registered_workers)))
            for worker in registered_workers:
                info = (worker['worker_id'], worker['username'], worker['queue'])
                log.info('worker-id:\t{}\tusername/queue:\t{}/{}'.format(*info))
            log.info("See 'anaconda build deregister --help' to remove workers listed above.")
        else:
            log.info(no_workers)

def register_worker(bs, args):
    '''
    Register the worker with anaconda
    '''
    worker_id = bs.register_worker(args.username, args.queue, args.platform,
                                        args.hostname, args.dist)
    log.info('Registered worker with worker_id:%s' % worker_id)
    args.worker_id = worker_id
    with open(args.output, 'w') as fd:
        yaml.dump(vars(args), fd)
    if os.path.exists(REGISTERED_WORKERS_FILE):
        with open(REGISTERED_WORKERS_FILE, 'r') as f:
            registered_workers = yaml.load(f.read())
            registered_workers.append(vars(args))
    else:
        registered_workers = [vars(args)]
    with open(REGISTERED_WORKERS_FILE, 'w') as f:
        f.write(yaml.dump(registered_workers))
    log.info('Worker config saved at %s.' % args.output)
    return args

def deregister_worker(bs, args):
    ''' Deregister the worker with anaconda'''
    try:
        config_file = args.config
        if config_file is not None:
            with open(config_file, 'r') as f:
                worker_config = yaml.load(f.read())
            args = Namespace()
            vars(args).update(worker_config)
        log.info("Removing worker %s." % args.worker_id)
        removed_worker = bs.remove_worker(args.username, args.queue, args.worker_id)
        if not removed_worker:
            info = (args.worker_id, args.username, args.queue,)
            raise errors.BinstarError('Failed to remove_worker with argument of ' + \
                                      'worker_id\t{}\tusername/queue\t{}/{}'.format(*info))
        registered_workers = []
        with open(REGISTERED_WORKERS_FILE, 'r') as f:
            registered_workers = yaml.load(f.read())
            for idx in range(len(registered_workers)):
                if registered_workers[idx]['worker_id'] == args.worker_id:
                    registered_workers.pop(idx)
        with open(REGISTERED_WORKERS_FILE, 'w') as f:
            f.write(yaml.dump(registered_workers))
        if config_file is not None:
            os.unlink(config_file)
            log.debug("Removed worker config %s" % config_file)
        return args
    except Exception as e:
        log.info('Failed on anaconda build deregister.\n')
        print_registered_workers()
        log.info('deregister failed with error:\n')
        raise