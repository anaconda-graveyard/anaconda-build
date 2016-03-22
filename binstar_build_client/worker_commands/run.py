'''
Build worker
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging
import os
import yaml

from clyent.logs import setup_logging
from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.register import WorkerConfiguration

log = logging.getLogger('binstar.build')

WRONG_HOSTNAME_MSG = 'Proceeding with worker id registered for ' + \
                     'different hostname: {}. ' + \
                     'This host is: {}.'


def main(args):
    bs = get_binstar(args, cls=BinstarBuildAPI)
    worker_config = WorkerConfiguration.load(args.worker_id, bs, warn=True)
    WorkerConfiguration.validate_worker_name(bs, args.worker_id)
    if worker_config.hostname != WorkerConfiguration.HOSTNAME:
        log.warn(WRONG_HOSTNAME_MSG.format(worker_config.hostname,
                                           WorkerConfiguration.HOSTNAME))
    args.conda_build_dir = args.conda_build_dir.format(platform=worker_config.platform)

    setup_logging(logging.getLogger('binstar_build_client'), args.log_level,
                  args.color, show_tb=args.show_traceback)

    log.info("Using conda build directory: {}".format(args.conda_build_dir))
    log.info(str(worker_config))

    worker = Worker(bs, worker_config, args)

    worker.write_status(True, "Starting")
    worker.write_stats()

    try:
        with worker_config.running():
            worker.work_forever()
    finally:
        worker.write_status(False, "Exited")


def add_parser(subparsers, name='run',
               description='Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__,
               default_func=main):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )
    parser.add_argument('worker_id',
                        help="worker_id that was given in anaconda build register")
    parser.add_argument('-f', '--fail', action='store_true',
                        help='Exit main loop on any un-handled exception')
    parser.add_argument('-1', '--one', action='store_true',
                        help='Exit main loop after only one build')
    parser.add_argument('--push-back', action='store_true',
                        help='Developers only, always push the build *back* ' + \
                             'onto the build queue')

    dgroup = parser.add_argument_group('development options')

    conda_prefix = get_conda_root_prefix()
    if conda_prefix:
        default_build_dir = os.path.join(conda_prefix, 'conda-bld', '{platform}')
    else:
        default_build_dir = None
    dgroup.add_argument("--conda-build-dir",
                        default=default_build_dir,
                        help="[Advanced] The conda build directory (default: %(default)s)",
                        )

    dgroup.add_argument('--show-new-procs', action='store_true', dest='show_new_procs',
                        help='Print any process that started during the build '
                             'and is still running after the build finished')

    dgroup.add_argument('--status-file',
                        help='If given, binstar will update this file with the ' + \
                             'time it last checked the anaconda server for updates')

    parser.add_argument('--cwd', default=os.path.abspath('.'), type=os.path.abspath,
                        help='The root directory this build should use (default: "%(default)s")')

    parser.add_argument('-t', '--max-job-duration', type=int, metavar='SECONDS',
                        dest='timeout',
                        help='Force jobs to stop after they exceed duration (default: %(default)s)', default=60 * 60)

    parser.set_defaults(main=default_func)
    return parser
