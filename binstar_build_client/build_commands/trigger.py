'''
Trigger a build that has been saved

See also:

  * [Save and Trigger Your Builds](http://docs.anaconda.org/build.html#SaveAndTriggerYourBuilds)
'''

from __future__ import print_function, unicode_literals, division, absolute_import

from argparse import RawDescriptionHelpFormatter
import logging

from binstar_build_client import BinstarBuildAPI
from binstar_client.utils import get_binstar
from binstar_client.utils import package_specs

from binstar_build_client.utils import get_anaconda_url
from binstar_build_client.build_commands.submit import (tail_sub_build,
                                                       add_tail_parser)
log = logging.getLogger('binstar.build')


def main(args):
    binstar = get_binstar(args, cls=BinstarBuildAPI)

    queue_tags = []
    if args.buildhost:
        queue_tags.append('hostname:{0}'.format(args.buildhost))
    if args.dist:
        queue_tags.append('dist:{0}'.format(args.dist))

    # TODO: change channels= to labels=
    build_no = binstar.trigger_build(
        args.package.user,
        args.package.name,
        channels=args.labels,
        queue_name=args.queue,
        queue_tags=queue_tags,
        branch=args.branch,
        test_only=args.test_only,
        filter_platform=args.platform)

    log.info('')

    url = get_anaconda_url(binstar, '/{package.user}/{package.name}/builds/matrix/{build_no}'.format(
        package=args.package,
        build_no=build_no,
    ))
    log.info('To view this build go to %s', url)
    log.info('')

    if args.tail:
        tail_sub_build(binstar, args, build_no)
    else:
        log.info(
            'You may also run\n\n    anaconda build tail -f %s/%s %s\n' % (args.package.user, args.package.name, build_no))
        log.info('')
        log.info('Build %s submitted' % build_no)


def add_parser(subparsers):
    description = 'Trigger a build that has been saved'
    parser = subparsers.add_parser('trigger',
                                   help=description,
                                   description=description,
                                   epilog=__doc__,
                                   formatter_class=RawDescriptionHelpFormatter,
                                   )

    parser.add_argument('package',
                        help="The Anaconda Cloud package to trigger a build on",
                        metavar='USER/PACKAGE',
                        type=package_specs)

    parser.add_argument('--channel', action='append', dest='labels',
                        help="[DEPRECATED] Upload targets to this channel")

    parser.add_argument('--label', action='append', dest='labels',
                        help="Upload targets to this label")

    parser.add_argument('--queue',
                        help="Build on this queue")

    parser.add_argument('--branch', default='master',
                        help="Branch to build"
                        )

    filters = parser.add_argument_group('filters')

    filters.add_argument('--buildhost',
                         help="The host name of the intended build worker")

    filters.add_argument('--dist',
                         help=("The os distribution of intended build worker (e.g centos, ubuntu) "
                               "Use 'anaconda build queue' to view the workers")
                         )

    filters.add_argument('--platform',
                         help=("The platform to run (e.g linux-64, win-64, osx-64, etc) "
                               "(default: all the platforms in the .binstar.yaml file)")
                         )

    filters.add_argument('--test-only', '--no-upload', action='store_true',
                         dest='test_only',
                         help="Don't upload the build targets to Anaconda Cloud, but run everything else")

    add_tail_parser(parser)
    parser.set_defaults(main=main)
