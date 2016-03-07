'''
List Anaconda build workers

anaconda worker list
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client.worker.register import WorkerConfiguration
from binstar_client.utils import get_binstar
from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import split_queue_arg

log = logging.getLogger('binstar.build')

def print_registered_workers(bs, args):

    has_workers = False

    log.info('Registered workers:')
    if args.queue:
        user, args.queue = split_queue_arg(args.queue)
    for wconfig in WorkerConfiguration.registered_workers(bs):
        has_workers = True
        if args.this_host_only and wconfig.hostname != WorkerConfiguration.HOSTNAME:
            continue
        if args.queue and args.queue != wconfig.queue:
            continue
        if args.org and args.org != wconfig.username:
            continue
        msg = '{name}, id:{worker_id}, hostname:{hostname}, queue:{username}/{queue}'.format(**wconfig.to_dict())
        if wconfig.pid:
            msg += ' (running with pid: {})'.format(wconfig.pid)

        log.info(msg)

    if not has_workers:
        log.info('(No registered workers)')

def main(args):

    bs = get_binstar(args, cls=BinstarBuildAPI)
    print_registered_workers(bs, args)

def add_parser(subparsers, name='list',
               description='List build workers and queues',
               epilog=__doc__):
    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.add_argument('--this-host-only',
                        '-t',
                        action='store_true',
                        help="Print only workers registered from this hostname.")
    parser.add_argument('--org',
                        '-o',
                        help="Print only workers registered in this organization")
    parser.add_argument('--queue',
                        '-q',
                        help="Print only workers registered to this queue.")
    parser.set_defaults(main=main)

    return parser
