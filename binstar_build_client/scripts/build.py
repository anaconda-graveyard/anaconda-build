'''
Binstar Build command

Initialize the build directory:

    binstar-build init

This will create a default .binstar.yml file in the current directory

Submit a build:

    binstar-build submit

Tail the output of a build until it is complete:

    binstar-build tail user/package 1.0

'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client import __version__ as version
from binstar_build_client import commands
from binstar_client.scripts.cli import binstar_main


logger = logging.getLogger('binstar')

def main(args=None, exit=True):
    description = 'Binstar build client for continuous integration, testing and building packages'
    return binstar_main(commands, args, exit,
                        epilog=__doc__, description=description,
                        version=version)


if __name__ == '__main__':
    main()
