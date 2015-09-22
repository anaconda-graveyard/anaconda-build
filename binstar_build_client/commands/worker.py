'''
Build worker 
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import Namespace
import logging
import os
import time
import yaml

from binstar_client.utils import get_binstar
from binstar_client import errors

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.worker import Worker

log = logging.getLogger('binstar.build')

def main(args):
    with open(args.worker_config) as f:
        worker_config = yaml.load(f.read())
    args = Namespace()
    vars(args).update(worker_config)
    args.conda_build_dir = args.conda_build_dir.format(args=args)
    bs = get_binstar(args, cls=BinstarBuildAPI)

    log.info('Starting worker:')
    log.info('User: %s' % args.username)
    log.info('Queue: %s' % args.queue)
    log.info('Platform: %s' % args.platform)

    worker = Worker(bs, args)
    worker.write_status(True, "Starting")
    try:
        worker.work_forever()
    finally:
        worker.write_status(False, "Exited")



def add_parser(subparsers, name='worker',
               description='Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.add_argument('worker_config', 
                        help="yaml config file produced as --output from anaconda build register")
    parser.set_defaults(main=main)
    return parser