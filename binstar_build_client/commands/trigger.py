'''
Trigger a build that has been saved

See also: 

  * [Save and Trigger Your Builds](http://docs.binstar.org/examples.html#SaveAndTriggerYourBuilds)
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import RawDescriptionHelpFormatter
import logging

from binstar_build_client import BinstarBuildAPI
from binstar_client.utils import get_binstar
from binstar_client.utils import package_specs

log = logging.getLogger('binstar.build')

def main(args):

    binstar = get_binstar(args, cls=BinstarBuildAPI)

    build_no = binstar.trigger_build(args.package.user, args.package.name,
                               channels=args.channels, queue_name=args.queue,
                               branch=args.branch, test_only=args.test_only,
                               filter_platform=args.platform)

    log.info('')
    log.info('To view this build go to http://alpha.binstar.org/%s/%s/builds/matrix/%s' % (args.package.user, args.package.name, build_no))
    log.info('')
    log.info('You may also run\n\n    binstar-build tail -f %s/%s %s\n' % (args.package.user, args.package.name, build_no))
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
                       help="The binstar package to trigger a build on",
                       metavar='USER/PACKAGE',
                       type=package_specs)

    parser.add_argument('--channel', action='append', dest='channels',
                       help="Upload targets to this channel")

    parser.add_argument('--queue',
                       help="Build on this queue")

    parser.add_argument('--branch', default='master',
                        help="Branch to build"
                        )

    parser.add_argument('--platform',
                        help="Only run the build for this platform, (filters list from .binstar.yml)"
                        )

    parser.add_argument('--test-only', '--no-upload', action='store_true',
                        dest='test_only',
                        help="Don't upload the build targets to binstar, but run everything else")


    parser.set_defaults(main=main)

