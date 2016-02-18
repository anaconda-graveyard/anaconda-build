'''
Register an anaconda build worker.

anaconda build register
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import platform
import logging

from binstar_client import errors
from binstar_client.utils import get_binstar
from binstar_build_client.utils.validate_name import is_valid_name
from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.register import (WorkerConfiguration,
                                                  split_queue_arg)


OS_MAP = {'darwin': 'osx', 'windows':'win'}
ARCH_MAP = {'x86': '32',
            'i686': '32',
            'x86_64': '64',
            'amd64' : '64',
            }

log = logging.getLogger('binstar.build')

def get_platform():
    'Get the conda platform string of the current machine'

    operating_system = platform.system().lower()
    arch = platform.machine().lower()
    return '{}-{}'.format(OS_MAP.get(operating_system, operating_system),
                      ARCH_MAP.get(arch, arch))

def get_dist():
    '''
    Get the current os and version
    '''
    if platform.dist()[0]:
        return platform.dist()[0].lower()
    elif platform.mac_ver()[0]:
        darwin_version = platform.mac_ver()[0].rsplit('.', 1)[0]
        return 'darwin%s' % darwin_version
    elif platform.win32_ver()[0]:
        return platform.win32_ver()[0].lower()
    return 'unknown'


def main(args):

    args.username, args.queue = split_queue_arg(args.queue)
    bs = get_binstar(args, cls=BinstarBuildAPI)

    if args.name:
        if not is_valid_name(args.name):
            raise errors.BinstarError('Invalid name for '
                                  'worker: {}.  Must start'
                                  ' with a letter and contain'
                                  ' only numbers, letters, -, and _'.format(args.name))

    worker_config = WorkerConfiguration.register(
        bs, args.username, args.queue,
        args.platform, args.hostname, args.dist,
        name=args.name,
    )

    log.info('When running, worker PID files will be at {}.<PID>.'.format(worker_config.filename))
    log.info('Now run:\n\tanaconda worker run {}'.format(worker_config.name))


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

    parser.add_argument('-n', '--name', metavar='WORKER_NAME',
                        help='Unique name of the worker')

    parser.add_argument('-p', '--platform',
                        default=conda_platform,
                        help='The platform this worker is running on (default: %(default)s)')

    parser.add_argument('--hostname', default=platform.node(),
                        help='The host name the worker should use (default: %(default)s)')

    parser.add_argument('--dist', default=get_dist(),
                        help='The operating system distribution the worker should use (default: %(default)s)')

    parser.set_defaults(main=main)

    return parser
