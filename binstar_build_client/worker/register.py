import os
import yaml
import logging
import tempfile

log = logging.getLogger("binstar.build")
STATE_FILE = 'worker.yaml'
def register_worker(args, bs):
    '''
    Register the worker with binstar and clean up on any excpetion or exit
    '''
    os.chdir(args.cwd)

    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE, 'r') as fd:
            worker_data = yaml.load(fd)

        bs.remove_worker(args.username, args.queue, worker_data['worker_id'])
        log.info("Un-registered worker %s from binstar site" % worker_data['worker_id'])
        os.unlink(STATE_FILE)
        log.info("Removed worker.yaml")

    worker_id = bs.register_worker(args.username, args.queue, args.platform,
                                        args.hostname, args.dist)
    log.info('Registered worker with worker_id:%s' % worker_id)
    worker_data = {'worker_id': worker_id}
    worker_data.update({'args': args.__dict__,})
    with open(STATE_FILE, 'w') as fd:
        yaml.dump(worker_data, fd)
    log.info('STATE_FILE %s' % STATE_FILE)

def deregister_worker(bs, args):
    os.chdir(args.cwd)
    with open(STATE_FILE) as f:
        worker_data = yaml.load(f.read())
    args = worker_data['args']
    log.info("Removing worker %s" % worker_data['worker_id'])
    try:
        bs.remove_worker(args['username'], args['queue'], worker_data['worker_id'])
        os.unlink(STATE_FILE)
    except Exception as err:
        log.exception(err)
    log.debug("Removed %s" % STATE_FILE)

