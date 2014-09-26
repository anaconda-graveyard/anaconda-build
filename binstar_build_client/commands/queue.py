'''
Build Queue
'''
from __future__ import (print_function, unicode_literals, division,
    absolute_import)
from binstar_client.utils import get_binstar, bool_input
from binstar_build_client import BinstarBuildAPI
from argparse import RawDescriptionHelpFormatter
from dateutil.parser import parse as parse_date
from binstar_client.commands.authorizations import format_timedelta
from binstar_client import errors

def show_queue(queue):
    queue_owner = queue.get('owner')
    platforms = ', '.join(queue.get('platforms', []))

    if queue_owner:
        queue_name = '{0}/{1}'.format(queue_owner['login'], queue['_id'])
    else:
        queue_name = queue['_id']
    print('{queue_name:30} [{platforms}]'.format(**locals()))
    for worker in queue.get('workers', []):
        print(' + Worker hostname:{worker[hostname]:15} platform:{worker[platform]:15} dist:{worker[dist]:15}'.format(**locals()))

        try:
            last_seen = parse_date(worker['last_seen'])
            last_seen = '%s ago' % format_timedelta(last_seen, False)
        except TypeError:
            last_seen = worker['last_seen']

        print('   - Id {0[id]}'.format(worker))
        print('   - Last seen {0}'.format(last_seen))
        print('   - binstar-build v{0[binstar_build_version]} (binstar v{0[binstar_version]})'.format(worker))
    if not queue.get('workers', []):
        print(" + No build workers attached to this queue")
    print()

def show_queues(bs, username):
    print()
    for queue in bs.build_queues(username):
        show_queue(queue)

def main(args):
    bs = get_binstar(args, cls=BinstarBuildAPI)

    if args.organization:
        username = args.organization
    else:
        user = bs.user()
        username = user['login']

    if args.create:

        if not args.platform:
            raise errors.BinstarError("Must specify at least one platform")

        bs.add_build_queue(username, args.queue, args.platform)
        print("Created queue %s" % args.queue)
        return

    if args.queue:
        queue = bs.build_queue(username, args.queue)

    if args.remove:
        if queue.get('workers'):
            prompt = ('This build queue still has workers attached. '
                      'Are you sure you want to remove it')
            if not bool_input(prompt, False):
                print("Not removing queue")
                return
        bs.remove_build_queue(username, args.queue)
        print("Removed queue %s" % args.queue)
        return

    if args.remove_worker:
        bs.remove_worker(username, args.queue, args.remove_worker)
        print("Removed worker %s from queue %s" % (args.remove_worker, args.queue))
        return


    if args.queue:
        print()
        show_queue(queue)
    else:
        show_queues(bs, username)

def add_parser(subparsers):
    parser = subparsers.add_parser('queue',
                                      help='Inspect build queue',
                                      description=__doc__,
                                      formatter_class=RawDescriptionHelpFormatter,
                                      )

    parser.add_argument('-o', '--organization',
                        help='Act as an organization')
    parser.add_argument('-q', '--queue', metavar='Q',
                        help='Specify a queue to perform an operation on')
    parser.add_argument('-r', '--remove', action='store_true',
                        help='Remove the queue specified with the -q/--queue option')
    parser.add_argument('-c', '--create', action='store_true',
                        help='Create a new queue')
    parser.add_argument('-p', '--platform', action='append', default=[],
                        help='Append a platform to the list (use with -c/--create option)')
    parser.add_argument('--remove-worker', metavar='WORKER_ID',
                        help='Remove a worker from a queue')

    parser.set_defaults(main=main)
