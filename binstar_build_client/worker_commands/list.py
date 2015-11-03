'''
List Anaconda build workers

anaconda worker list
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from binstar_build_client.worker.register import WorkerConfiguration

import logging
log = logging.getLogger('binstar.build')


def main(args):

    log.info('Registered workers:\n')
    WorkerConfiguration.print_registered_workers(as_json=args.json)

def add_parser(subparsers, name='list',
               description='List build workers and queues',
               epilog=__doc__):
    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.add_argument('-j','--json',
                        help="Output as json for machine reading.",
                        action="store_true")
    parser.set_defaults(main=main)

    return parser
