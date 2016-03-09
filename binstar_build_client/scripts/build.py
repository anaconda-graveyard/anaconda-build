'''
Anaconda Build command

To get started with anaconda build run:

    anaconda build init
    anaconda build submit .

See also:

  * [Anaconda Build](http://docs.anaconda.org/building.html)

'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client import __version__ as version
from binstar_build_client import build_commands
from binstar_client.scripts.cli import binstar_main
from argparse import RawDescriptionHelpFormatter
from clyent import add_subparser_modules


logger = logging.getLogger('binstar')

description = 'Anaconda build client for continuous integration, testing and building packages'
def add_parser(subparsers):
    parser = subparsers.add_parser('build',
                                      help=description,
                                      epilog=__doc__,
                                      formatter_class=RawDescriptionHelpFormatter,

                                      )

    parser.add_argument('-V', '--version',
                        action='version',
                        version='anaconda-build {}'.format(version))

    add_subparser_modules(parser, build_commands, 'conda_server_build.subcommand')


def main(args=None, exit=True):
    description = 'Anaconda build client for continuous integration, testing and building packages'

    return binstar_main(build_commands, args, exit,
                        epilog=__doc__, description=description,
                        version=version)


if __name__ == '__main__':
    main()
