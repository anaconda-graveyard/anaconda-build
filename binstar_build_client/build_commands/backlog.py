'''
Build queue backlog
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import logging

from binstar_build_client import BinstarBuildAPI
from binstar_client.utils import get_binstar
from binstar_client import errors
from pprint import pprint

log = logging.getLogger('binstar.build')


def main(args):

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
    backlog = bs.build_backlog(args.username, args.queue)


    print("Backlog for queue %s/%s" % (args.username, args.queue))
    header = {'name': 'Package', 'build_no': 'Build', 'tags': 'Platform', 'enqueued': 'Enqueued'}
    print('%(name)-30s | %(build_no)-10s | %(tags)-10s | %(enqueued)-30s' % header)
    print ('-' * 89)
    for job in backlog:
        job['tags'] = ', '.join(job['tags'])
        print('%(name)-30s | %(build_no)10s | %(tags)10s | %(enqueued)30s' % job)

def add_parser(subparsers, name='backlog',
               description='Run a build worker to build jobs off of a anaconda build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )

    parser.add_argument('queue', metavar='OWNER/QUEUE',
                        help='The queue to pull builds from')

    parser.set_defaults(main=main)
    return parser

