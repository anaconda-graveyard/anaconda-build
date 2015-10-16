from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import yaml

from binstar_client import errors
from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import WorkerConfiguration

def main(args, context="worker"):

    bs = get_binstar(args, cls=BinstarBuildAPI)

    wconfig = WorkerConfiguration.load(args.worker_id)
    wconfig.deregister(bs)


def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__,
               default_func=main):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog)
    parser.add_argument('-l', '--list',
                        help='List the workers registered by this user/machine and exit.',
                        action='store_true')
    parser.add_argument('worker_id',
                        help="Worker id (required if no --config arg")
    parser.set_defaults(main=default_func)
    return parser
