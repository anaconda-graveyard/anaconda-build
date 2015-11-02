'''

anaconda build worker is DEPRECATED.


Use:


anaconda worker -h

to see worker and docker-worker CLI usage.


'''

import argparse

from binstar_build_client.worker_commands.run import add_parser as add_parser_run


def main(args):
    print(__doc__)

def add_parser(subparsers, name='worker',
               description='DEPRECATED: use anaconda worker -h',
               epilog=__doc__,
               default_func=main):
    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.add_argument('-q','--queue')
    parser.add_argument('placeholder', nargs="*")
    parser.add_help=False

    parser.set_defaults(main=main)




