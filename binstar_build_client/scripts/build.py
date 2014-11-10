'''
Binstar Build command

To get started with binstar build run:

    binstar-build init
    binstar-build submit

See also: 

  * [Binstar Build](http://docs.binstar.org/examples.html#BinstarBuild)
  
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
