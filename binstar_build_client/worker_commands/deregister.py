from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import logging
import platform
import yaml


from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import WorkerConfiguration

log = logging.getLogger('binstar.build')

context_info = """Use one of:
    anaconda worker deregister --all
    anaconda worker deregister <some-worker-id>
See also:
    anaconda worker deregister -h
"""
def main(args, context="worker"):

    bs = get_binstar(args, cls=BinstarBuildAPI)
    if args.all:
        WorkerConfiguration.deregister_all(bs)
    elif args.worker_id:
        wconfig = WorkerConfiguration.load(args.worker_id, bs)
        wconfig.deregister(bs)
    else:
        log.info(context_info)

def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__,
               default_func=main):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog)
    parser.add_argument('worker_id',
                        help="Worker id to deregister",
                        nargs="?")
    parser.add_argument('-a','--all',
                        help="Deregister all workers " +\
                             "registered by this hostname {}.".format(platform.node()),
                        action="store_true")
    parser.set_defaults(main=default_func)
    return parser
