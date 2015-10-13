'''
Register an anaconda build worker.

anaconda build register
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
import platform

from binstar_build_client.worker.register import register_worker_main

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

def main(args):
    return register_worker_main(args, context="worker")

def add_parser(subparsers, name='register',
               description='Register a build worker to build jobs off of a binstar build queue',
               epilog=__doc__,
               default_func=main):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )

    conda_platform = get_platform()
    parser.add_argument('queue', metavar='OWNER/QUEUE',
                        help='The queue to pull builds from')
    parser.add_argument('-p', '--platform',
                        default=conda_platform,
                        help='The platform this worker is running on (default: %(default)s)')

    parser.add_argument('--hostname', default=platform.node(),
                        help='The host name the worker should use (default: %(default)s)')

    parser.add_argument('--dist', default=get_dist(),
                        help='The operating system distribution the worker should use (default: %(default)s)')

    parser.add_argument('--cwd', default=os.path.abspath('.'), type=os.path.abspath,
                        help='The root directory this build should use (default: "%(default)s")')
    parser.add_argument('-t', '--max-job-duration', type=int, metavar='SECONDS',
                        dest='timeout',
                        help='Force jobs to stop after they exceed duration (default: %(default)s)', default=60 * 60)
    parser.set_defaults(main=default_func)

    return parser
