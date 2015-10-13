'''
List Anaconda build workers

anaconda worker list
anaconda docker_worker list
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)


from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import show_registration_info


def main(args):
    bs = get_binstar(args, cls=BinstarBuildAPI)
    show_registration_info(bs, args)

def add_parser(subparsers, name='list',
               description='List build workers and queues',
               epilog=__doc__):
    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.set_defaults(main=main)

    return parser
