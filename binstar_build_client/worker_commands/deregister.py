from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import yaml
import logging

from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import WorkerConfiguration

log = logging.getLogger('bisntar.build')

def main(args, context="worker"):
    if args.json:
        old_log_level = args.log_level
        args.log_level = -1
    bs = get_binstar(args, cls=BinstarBuildAPI)
    if args.json:
        args.log_level = old_log_level
    wconfig = WorkerConfiguration.load(args.worker_id)
    wconfig.deregister(bs, as_json=args.json)

    os.unlink(wconfig.filename)
    if not args.json:
        log.debug("Removed worker config {}".format(wconfig.filename))


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
    parser.add_argument('-j','--json',
                        help="Output as json for machine reading",
                        action="store_true")
    parser.set_defaults(main=default_func)
    return parser
