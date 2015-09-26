'''
Register an anaconda build worker.

anaconda build register 
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)
import os
import tempfile
import platform
from argparse import RawDescriptionHelpFormatter

from dateutil.parser import parse as parse_date
from binstar_client.commands.authorizations import format_timedelta
from binstar_client import errors
from binstar_client.utils import get_binstar, bool_input

from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import register_worker

    
    
OS_MAP = {'darwin': 'osx', 'windows':'win'}
ARCH_MAP = {'x86': '32',
            'i686': '32',
            'x86_64': '64',
            'amd64' : '64',
            }

def get_platform():
    operating_system = platform.system().lower()
    arch = platform.machine().lower()
    return '%s-%s' % (OS_MAP.get(operating_system, operating_system),
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
    if not args.output:
        args.output = tempfile.NamedTemporaryFile(delete=False).name
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
    parser.add_argument('queue', metavar='OWNER/QUEUE',
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
    parser.add_argument('-o','--output',
                        help="Filename of output worker config yaml file with worker id and args.")
    dgroup = parser.add_argument_group('development options')

    dgroup.add_argument("--conda-build-dir",
                        default=os.path.join(get_conda_root_prefix(), 'conda-bld', '{args.platform}'),
                        help="[Advanced] The conda build directory (default: %(default)s)",
                        )
    dgroup.add_argument('--show-new-procs', action='store_true', dest='show_new_procs',
                        help='Print any process that started during the build '
                             'and is still running after the build finished')

    dgroup.add_argument('-c', '--clean', action='store_true',
                        help='Clean up an existing workers session')
    dgroup.add_argument('-f', '--fail', action='store_true',
                        help='Exit main loop on any un-handled exception')
    dgroup.add_argument('-1', '--one', action='store_true',
                        help='Exit main loop after only one build')
    dgroup.add_argument('--push-back', action='store_true',
                        help='Developers only, always push the build *back* onto the build queue')

    dgroup.add_argument('--status-file',
                        help='If given, binstar will update this file with the time it last checked the anaconda server for updates')

    parser.set_defaults(main=main)

    return parser

