'''
Anaconda Build command

To get started with anaconda worker run:

    anaconda worker register USER/QUEUE -n NAME
    anaconda worker run NAME

See also:

  * [Anaconda Build](http://docs.anaconda.org/build-config.html#BuildWorkers)

'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client import __version__ as version
from binstar_build_client import worker_commands
from binstar_client.scripts.cli import binstar_main
from argparse import RawDescriptionHelpFormatter
from clyent import add_subparser_modules


logger = logging.getLogger('binstar')

description = 'Anaconda build client for continuous integration, testing and building packages'
def add_parser(subparsers):
    parser = subparsers.add_parser('worker',
                                      help=description,
                                      epilog=__doc__,
                                      formatter_class=RawDescriptionHelpFormatter,
                                      )

    add_subparser_modules(parser, worker_commands, 'conda_server_build.subcommand')


def main(args=None, exit=True):
    description = 'Anaconda build client for continuous integration, testing and building packages'

    return binstar_main(worker_commands, args, exit,
                        epilog=__doc__, description=description,
                        version=version)


if __name__ == '__main__':
    main()
