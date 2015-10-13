'''
Build worker
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_client import errors
from binstar_client.utils import get_binstar

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.docker_worker import DockerWorker
from binstar_build_client.worker.register import Registration
from binstar_build_client.worker_commands.run import add_parser as add_run_parser

try:
    import docker
except ImportError:
    docker = None

log = logging.getLogger('binstar.build')


def main(args):
    if docker is None:
        raise errors.UserError("anaconda docker-worker [run|register|deregister|list] requires docker and docker-py to be installed\n"
                               "Run:\n\tpip install docker-py")
    bs = get_binstar(args, cls=BinstarBuildAPI)
    reg = Registration.load(bs, args.worker_id)
    reg.clean_workers_dir(bs)
    reg.assert_is_not_running(bs)
    reg.is_running = True
    reg.save()
    try:
        worker = DockerWorker(bs, args, reg)
        worker.work_forever()
    finally:
        reg.is_running = False
        reg.save()

def add_parser(subparsers):
    description = 'Run a build worker in a docker container to build jobs off of a binstar build queue'

    parser = add_run_parser(subparsers, 'run',
                               description, __doc__)

    dgroup = parser.add_argument_group('docker arguments')
    dgroup.add_argument("-i", "--image", default="binstar/linux-64",
                        help="Docker image to use (default %(default)s)",
                        )
    dgroup.add_argument('--allow-user-images', action='store_true', default=False,
                        help="Allow user defined images")

    parser.set_defaults(main=main,
                        platform="linux-64",
                        conda_build_dir="/opt/miniconda/conda-bld/linux-64")


