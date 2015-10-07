'''
Register an anaconda build worker.

anaconda build register 
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import platform
import tempfile

from binstar_client import errors
from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import (register_worker,
                                                  print_registered_workers,)
 
OS_MAP = {'darwin': 'osx', 'windows':'win'}
ARCH_MAP = {'x86': '32',
            'i686': '32',
            'x86_64': '64',
            'amd64' : '64',
            }

def get_platform():
    operating_system = platform.system().lower()
    arch = platform.machine().lower()
    return '{}-{}'.format(OS_MAP.get(operating_system, operating_system),
                      ARCH_MAP.get(arch, arch))

def get_dist():
    if platform.dist()[0]:
        return platform.dist()[0].lower()
    elif platform.mac_ver()[0]:
        darwin_version = platform.mac_ver()[0].rsplit('.', 1)[0]
        return 'darwin%s' % darwin_version
    elif platform.win32_ver()[0]:
        return platform.win32_ver()[0].lower()
    return 'unknown'

def split_queue_arg(queue):
    if queue.count('/') == 1:
        username, queue = queue.split('/', 1)
    elif queue.count('-') == 2:
        _, username, queue = queue.split('-', 2)
    else:
        raise errors.UserError("Build queue must be of the form build-USERNAME-QUEUENAME or USERNAME/QUEUENAME")
    return username, queue

def main(args):
    if args.list:
        print_registered_workers()
        return
    if not args.queue:
        raise errors.BinstarError('Argument --queue <USERNAME>/<QUEUE> is required.')
    args.username, args.queue = split_queue_arg(args.queue)
    bs = get_binstar(args, cls=BinstarBuildAPI)
    return register_worker(bs, args)

def add_parser(subparsers, name='register',
               description='Register a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )

    conda_platform = get_platform()
    parser.add_argument('-l', '--list', 
                        help='List the workers registered by this user/machine and exit.',
                        action='store_true')
    parser.add_argument('-q', '--queue', metavar='OWNER/QUEUE',
                        help='The queue to pull builds from')
    parser.add_argument('-p', '--platform',
                        default=conda_platform,
                        help='The platform this worker is running on (default: %(default)s)')

    parser.add_argument('--hostname', default=platform.node(),
                        help='The host name the worker should use (default: %(default)s)')

    parser.add_argument('--dist', default=get_dist(),
                        help='The operating system distribution the worker should use (default: %(default)s)')

    parser.add_argument('--cwd', default='.',
                        help='The root directory this build should use (default: "%(default)s")')
    parser.add_argument('-t', '--max-job-duration', type=int, metavar='SECONDS',
                        dest='timeout',
                        help='Force jobs to stop after they exceed duration (default: %(default)s)', default=60 * 60 * 60)
    parser.set_defaults(main=main)

    return parser
