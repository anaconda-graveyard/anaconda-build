'''
Binstar Build command

Initialize the build directory:

    binstar-build init

This will create a default .binstar.yml file in the current directory

Submit a build:

    binstar-build submit

Tail the output of a build untill it is complete:

    binstar-build tail user/package 1.0

'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client import __version__ as version
from binstar_client.scripts.cli import binstar_main

from ..commands import sub_commands


logger = logging.getLogger('binstar')

def main(args=None, exit=True):
    return binstar_main(sub_commands, args, exit,
                        description=__doc__, version=version)
