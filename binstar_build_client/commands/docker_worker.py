'''
Build worker 
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.worker.docker_worker import DockerWorker
from binstar_client.utils import get_binstar

from .worker import add_parser as add_worker_parser
from binstar_client import errors

try:
    import docker
except ImportError:
    docker = None

log = logging.getLogger('binstar.build')


def main(args):
    if docker is None:
        raise errors.UserError("binstar-build docker-worker requires docker and dockerpy to be installed\n"
                               "Run:\n\tpip install dockerpy")

    bs = get_binstar(args, cls=BinstarBuildAPI)

    if not args.username:
        current_user = bs.user()
        args.username = current_user['login']

    log.info('Starting worker:')
    log.info('User: %s' % args.username)
    log.info('Queue: %s' % args.queue)
    log.info('Platform: %s' % args.platform)
    woker = DockerWorker(bs, args)
    woker.work_forever()

def add_parser(subparsers):
    parser = add_worker_parser(subparsers, 'docker-worker',
                               'Build worker', __doc__)
    parser.add_argument("-i", "--image", default="binstar/linux-64",
                        help="Docker image to use (default %(default)s)",
                        )
    parser.add_argument('--allow-user-images', action='store_true', default=False,
                        help="Allow user defined images")

    parser.set_defaults(main=main,
                        platform="linux-64",
                        conda_build_dir="/opt/miniconda/conda-bld/linux-64")


