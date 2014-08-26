'''
Build worker 
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging
import os
import sys

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.worker import Worker
from binstar_client.utils import get_binstar

if sys.platform == 'win32':
    import platform
    uname = platform.uname
else:
    uname = os.uname

log = logging.getLogger('binstar.build')


def main(args):
    bs = get_binstar(args, cls=BinstarBuildAPI)

    if not args.username:
        current_user = bs.user()
        args.username = current_user['login']

    log.info('Starting worker:')
    log.info('User: %s' % args.username)
    log.info('Queue: %s' % args.queue)
    log.info('Platform: %s' % args.platform)
    woker = Worker(bs, args)
    woker.work_forever()


OS_MAP = {'darwin': 'osx', 'windows':'win32'}
ARCH_MAP = {'x86': '32',
            'x86_64': '64',
			'amd64' : '64'
            }

def get_platform():
    operating_system = uname()[0].lower()
    arch = uname()[4].lower()
    return '%s-%s' % (OS_MAP.get(operating_system, operating_system),
                      ARCH_MAP.get(arch, arch))

def add_parser(subparsers):
    parser = subparsers.add_parser('worker',
                                      help='Build Worker',
                                      description=__doc__,
                                      )

    parser.add_argument('queue',
                        help='The queue to pull builds from')
    parser.add_argument('-p', '--platform',
                        default=get_platform(),
                        help='The platform this worker is running on (default: %(default)s)')
    parser.add_argument('--hostname', default=uname()[1],
                        help='The host name the worker should use (default: %(default)s)')
    parser.add_argument('--cwd', default='.',
                        help='The root directory this build should use (default: "%(default)s")')
    parser.add_argument('-u', '--username', '--owner',
                        help='The queue\'s owner (defaults to your currently logged in binstar user account)')
    parser.add_argument('-c', '--clean', action='store_true',
                        help='Clean up an existing workers session')

    parser.set_defaults(main=main)

