import os
import yaml
import logging
import tempfile
from binstar_client import errors
from argparse import Namespace
log = logging.getLogger("binstar.build")

def register_worker(bs, args):
    '''
    Register the worker with binstar
    '''
    worker_id = bs.register_worker(args.username, args.queue, args.platform,
                                        args.hostname, args.dist)
    log.info('Registered worker with worker_id:%s' % worker_id)
    args.worker_id = worker_id
    with open(args.output, 'w') as fd:
        yaml.dump(args.__dict__, fd)
    log.info('Worker config saved at %s.' % args.output)
    return args

def deregister_worker(bs, args):
    config_file = args.config
    if config_file is not None:
        with open(config_file) as f:
            worker_config = yaml.load(f.read())
        args = Namespace()
        args.__dict__.update(worker_config)
    log.info("Removing worker %s." % args.worker_id)
    try:
        bs.remove_worker(args.username, args.queue, args.worker_id)
        if config_file is not None:
            os.unlink(config_file)
            log.debug("Removed worker config %s" % config_file)
    except Exception as err:
        log.exception(err)
    return args
