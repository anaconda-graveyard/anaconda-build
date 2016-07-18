'''
Build worker
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_client import errors
from binstar_client.utils import get_binstar
from clyent.logs import setup_logging

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.docker_worker import DockerWorker
from binstar_build_client.worker_commands.run import add_parser as add_worker_parser
from binstar_build_client.worker_commands.run import WRONG_HOSTNAME_MSG
from binstar_build_client.worker.register import WorkerConfiguration

try:
    import docker
except ImportError:
    docker = None

log = logging.getLogger('binstar.build')


def main(args):
    if docker is None:
        raise errors.UserError("anaconda worker docker_run requires docker and docker-py to be installed\n"
                               "Run:\n\tpip install docker-py")

    bs = get_binstar(args, cls=BinstarBuildAPI)
    worker_config = WorkerConfiguration.load(args.worker_id, bs, warn=True)
    WorkerConfiguration.validate_worker_name(bs, args.worker_id)
    if worker_config.hostname != WorkerConfiguration.HOSTNAME:
        log.warn(WRONG_HOSTNAME_MSG.format(worker_config.hostname,
                                           WorkerConfiguration.HOSTNAME))

    setup_logging(logging.getLogger('binstar_build_client'), args.log_level,
                  args.color, show_tb=args.show_traceback)

    worker = DockerWorker(bs, worker_config, args)
    worker.write_stats()
    worker.work_forever()

def add_parser(subparsers):
    description = 'Run a build worker in a docker container to build jobs off of a binstar build queue'

    parser = add_worker_parser(subparsers, 'docker_run',
                               description, __doc__)

    dgroup = parser.add_argument_group('docker arguments')
    dgroup.add_argument("-i", "--image", default="continuumio/anaconda-build-linux-64",
                        help="Docker image to use (default %(default)s)",
                        )
    dgroup.add_argument('--allow-user-images', action='store_true', default=False,
                        help="Allow user defined images")

    parser.set_defaults(main=main,
                        platform="linux-64",
                        conda_build_dir="/opt/miniconda/conda-bld/linux-64")


