'''
Build worker
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging
import os

from binstar_client import errors
from binstar_client.utils import get_binstar
import yaml

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.register import (REGISTERED_WORKERS_DIR,
                                                  print_registered_workers)

log = logging.getLogger('binstar.build')


def print_worker_summary(args, starting='worker'):
    log.info('Starting {}:'.format(starting))
    log.info('Hostname: {}'.format(args.hostname))
    log.info('User: {}'.format(args.username))
    log.info('Queue: {}'.format(args.queue))
    log.info('Platform: {}'.format(args.platform))
    log.info('Worker-id: {}'.format(args.worker_id))
    log.info('Build Options:')
    log.info('--conda-build-dir: {}'.format(args.conda_build_dir))
    log.info('--show-new-procs: {}'.format(args.show_new_procs))
    log.info('--status-file: {}'.format(args.status_file))
    log.info('--push-back: {}'.format(args.push_back))
    log.info('--one: {}'.format(args.one))
    log.info('--dist: {}'.format(args.dist))
    log.info('--cwd: {}'.format(args.cwd))
    log.info('--max-job-duration: {} (seconds)'.format(args.timeout))


def update_args_from_worker_file(args):
    worker_file = os.path.join(REGISTERED_WORKERS_DIR, args.worker_id)
    if not os.path.exists(worker_file):
        print_registered_workers()
        msg = '''Could not find worker config file at {}.
              See anaconda build register --help.'''.format(worker_file)
        raise errors.BinstarError(msg)
    with open(worker_file) as f:
        worker_config = yaml.load(f.read())
    vars(args).update(worker_config)
    args.conda_build_dir = args.conda_build_dir.format(args=args)
    return args


def main(args):
    args = update_args_from_worker_file(args)
    bs = get_binstar(args, cls=BinstarBuildAPI)
    print_worker_summary(args, starting='worker')
    worker = Worker(bs, args)
    worker.write_status(True, "Starting")
    try:
        worker.work_forever()
    finally:
        worker.write_status(False, "Exited")


def add_parser(subparsers, name='worker',
               description='Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

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
                        help='Developers only, always push the build *back* '
                             'onto the build queue')
    dgroup = parser.add_argument_group('development options')

    dgroup.add_argument("--conda-build-dir",
                        default=os.path.join(get_conda_root_prefix(),
                                             'conda-bld', '{args.platform}'),
                        help="[Advanced] The conda build directory (default: %(default)s)",
                        )
    dgroup.add_argument('--show-new-procs', action='store_true', dest='show_new_procs',
                        help='Print any process that started during the build '
                             'and is still running after the build finished')

    dgroup.add_argument('--status-file',
                        help='If given, binstar will update this file with the '
                             'time it last checked the anaconda server for updates')

    parser.set_defaults(main=main)
    return parser
