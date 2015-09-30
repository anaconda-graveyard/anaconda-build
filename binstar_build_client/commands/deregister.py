from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import RawDescriptionHelpFormatter
import os
import yaml

from binstar_client import errors
from binstar_client.commands.authorizations import format_timedelta
from binstar_client.utils import get_binstar, bool_input
from dateutil.parser import parse as parse_date

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.commands.register import split_queue_arg
from binstar_build_client.worker.register import (deregister_worker,
                                                  print_registered_workers)

def main(args):
    
    if args.list:
        print_registered_workers()
        return
    if args.config is not None:
        if not os.path.exists(args.config):
            raise errors.BinstarError('build worker --config file {} does not exist.'.format(args.config))
        with open(args.config, 'r') as f:
            vars(args).update(yaml.load(f.read()))
    else:
        if args.worker_id is None:
            raise errors.BinstarError('Argument --worker-id must not be None if --config is None')
    bs = get_binstar(args, cls=BinstarBuildAPI)
    return deregister_worker(bs, args)

def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog)
    parser.add_argument('-l', '--list', 
                        help='List the workers registered by this user/machine and exit.',
                        action='store_true')
    parser.add_argument('-c', '--config',
                        help='Path to a yaml config file that was an --output of anaconda build register')
    parser.add_argument('-q', '--queue',
                        help="Queue (required if no --config arg)")
    parser.add_argument('-w', '--worker-id',    
                        help="Worker id (required if no --config arg")
    parser.set_defaults(main=main)
    return parser
