from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from binstar_build_client.worker.register import (deregister_worker_main,
                                                  REGISTERED_WORKERS_DIR)

def main(args):
    return deregister_worker_main(args, context="worker")

def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__,
               default_func=main):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog)
    parser.add_argument('worker_id',
                        help=('Worker id or path to a '
                             'worker config file in {}').format(REGISTERED_WORKERS_DIR))
    parser.set_defaults(main=default_func)
    return parser
