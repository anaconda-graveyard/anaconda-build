'''
Build worker that runs as a root main process and uses su - build_user
to run builds as a lesser user.  The lesser user is named at startup, and
it is important to note that the home directory of the build_user is
destroyed and recreated from /etc/worker-skel on each build.
'''

from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import logging
import os

from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.worker.su_worker import (SuWorker,
                                                   SU_WORKER_DEFAULT_PATH)
from binstar_build_client.worker.register import WorkerConfiguration
from binstar_build_client.worker_commands.run import add_worker_dev_options

log = logging.getLogger('binstar.build')


def main(args):
    worker_config = WorkerConfiguration.load(args.worker_id)


    log.info(str(worker_config))
    worker_home = os.path.expanduser('~{0}'.format(args.build_user))

    args.conda_build_dir = os.path.join(worker_home, 'conda-bld', worker_config.platform)
    log.info("Using conda build directory: {}".format(args.conda_build_dir))

    bs = get_binstar(args, cls=BinstarBuildAPI)

    worker = SuWorker(bs, worker_config, args)

    worker.write_status(True, "Starting")

    try:
        with worker_config.running(build_user=args.build_user):
            worker.work_forever()
    finally:
        worker.write_status(False, "Exited")


def add_parser(subparsers, name='su_run',
               description='Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )

    parser.add_argument('worker_id',
                        help="worker_id that was given in anaconda build register")
    parser.add_argument('build_user',
                        help="Build user whose home directory is DELETED on each build.")
    parser.add_argument('--python-install-dir', default=SU_WORKER_DEFAULT_PATH,
                        help='sys.prefix for the root python install, not the '
                             'anaconda.org environment. Often /opt/anaconda.')
    parser.add_argument('-f', '--fail', action='store_true',
                        help='Exit main loop on any un-handled exception')
    parser.add_argument('-1', '--one', action='store_true',
                        help='Exit main loop after only one build')
    parser.add_argument('--push-back', action='store_true',
                        help='Developers only, always push the build *back* '
                             'onto the build queue')
    parser = add_worker_dev_options(parser)
    parser.set_defaults(main=main)

    return parser
