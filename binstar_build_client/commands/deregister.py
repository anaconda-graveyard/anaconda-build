from __future__ import (print_function, unicode_literals, division,
    absolute_import)
import os
from binstar_client.utils import get_binstar, bool_input
from binstar_build_client import BinstarBuildAPI
from argparse import RawDescriptionHelpFormatter
from dateutil.parser import parse as parse_date
from binstar_client.commands.authorizations import format_timedelta
from binstar_client import errors
from binstar_build_client.worker.register import deregister_worker

def main(args):
    
    if args.config is not None:
        if not os.path.exists(args.config):
            raise errors.BinstarError('build worker --config file %s does not exist.' % args.config)
    else:
        if args.username is None:
            raise errors.BinstarError('--username must not be None if --config is None')
        if args.queue is None:
            raise errors.BinstarError('--queue must not be None if --config is None')
        if args.worker_id is None:
            raise errors.BinstarError('--worker-id must not be None if --config is None')
    bs = get_binstar(args, cls=BinstarBuildAPI)
    return deregister_worker(bs, args)

def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog)
    parser.add_argument('-c', '--config',
                        help='Path to a config file from anaconda build register ...')
    parser.add_argument('-u', '--username', 
                        help="Username (required if no --config arg")
    parser.add_argument('-q', '--queue',
                        help="Queue (required if no --config arg)")
    parser.add_argument('-w', '--worker-id',
                        help="Worker id (required if no --config arg")
    parser.set_defaults(main=main)
    return parser