'''
Build worker that runs as a root main process and uses su - build_user
to run builds as a lesser user.  The lesser user is named at startup, and 
it is important to note that the home directory of the build_user is 
destroyed and recreated from /etc/worker-skel on each build. 
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging
import platform
import time
import os

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.su_worker import SuWorker, SU_WORKER_DEFAULT_PATH
from binstar_client.utils import get_binstar
from binstar_build_client.utils import get_conda_root_prefix
from binstar_client import errors
from .worker import OS_MAP, ARCH_MAP, get_platform, get_dist

log = logging.getLogger('binstar.build')

def main(args):

    python_install_dir = getattr(args, 'python_install_dir', SU_WORKER_DEFAULT_PATH)
    if args.conda_build_dir is None:
        args.conda_build_dir = os.path.join(python_install_dir, 
                                            'conda-bld', 
                                            '{args.platform}')
    args.conda_build_dir = args.conda_build_dir.format(args=args)
    bs = get_binstar(args, cls=BinstarBuildAPI)
    if args.queue.count('/') == 1:
        username, queue = args.queue.split('/', 1)
        args.username = username
        args.queue = queue
    elif args.queue.count('-') == 2:
        _, username, queue = args.queue.split('-', 2)
        args.username = username
        args.queue = queue
    else:
        raise errors.UserError("Build queue must be of the form build-USERNAME-QUEUENAME or USERNAME/QUEUENAME")
    log.info('Starting worker:')
    log.info('User: %s' % args.username)
    log.info('Queue: %s' % args.queue)
    log.info('Platform: %s' % args.platform)

    worker = SuWorker(bs, args, args.build_user, python_install_dir)
    worker.write_status(True, "Starting")
    try:
        worker.work_forever()
    finally:
        worker.write_status(False, "Exited")


def add_parser(subparsers, name='su_worker',
               description='Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )

    conda_platform = get_platform()
    parser.add_argument('queue', metavar='OWNER/QUEUE',
                        help='The queue to pull builds from')
    parser.add_argument('build_user',
                        help="Build user whose home directory is DELETED on each build.")
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

    parser.add_argument('--python-install-dir', default=SU_WORKER_DEFAULT_PATH,
                        help='sys.prefix for the root python install, not the anaconda.org environment. '+\
                             'Often /opt/anaconda.')
    dgroup = parser.add_argument_group('development options')

    dgroup.add_argument("--conda-build-dir",
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

