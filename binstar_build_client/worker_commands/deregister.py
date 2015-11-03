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

def main(args, context="worker"):

    bs = get_binstar(args, cls=BinstarBuildAPI)
    if args.worker_id.lower() == 'all':
        WorkerConfiguration.deregister_all(bs)
    else:
        wconfig = WorkerConfiguration.load(args.worker_id)
        wconfig.deregister(bs)
        os.unlink(wconfig.filename)
        log.debug("Removed worker config {0}".format(wconfig.filename))


def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__,
               default_func=main):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog)
    parser.add_argument('worker_id',
                        help="Worker id to deregister or \"all\" to " +\
                             "deregister all workers registered by this " +\
                             "hostname: {0}".format(platform.node()),
                        )
    parser.set_defaults(main=default_func)
    return parser
