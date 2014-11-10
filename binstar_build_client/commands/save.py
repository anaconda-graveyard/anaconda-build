'''
Save build info to be triggered later

See also: 

  * [Save and Trigger Your Builds](http://docs.binstar.org/examples.html#SaveAndTriggerYourBuilds)

'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import RawDescriptionHelpFormatter
import logging
import re

from binstar_build_client import BinstarBuildAPI
from binstar_client import errors
from binstar_client.utils import get_binstar, PackageSpec
from binstar_client.utils import package_specs
from six.moves.urllib.parse import urlparse
from binstar_build_client.utils.git_utils import get_gitrepo

log = logging.getLogger('binstar.build')

def main(args):

    binstar = get_binstar(args, cls=BinstarBuildAPI)

    # Force user auth

    package_name = None

    url = urlparse(args.url)
    builds = get_gitrepo(url)
    ghowner, ghrepo = builds['repo'].split('/', 1)

    if not args.package:
        package_name = ghrepo
        log.info("Using repo name '%s' as the pkg name." % package_name)
        user = binstar.user()
        user_name = user['login']
        args.package = PackageSpec(user_name, package_name)

    binstar = get_binstar(args, cls=BinstarBuildAPI)

    try:
        _ = binstar.package(args.package.user, args.package.name)
    except errors.NotFound:
        raise errors.UserError("Package %s does not exist" % (args.package,))

    log.info("Submitting the following repo for package creation: %s" % args.url)


    binstar.add_ci(args.package.user, args.package.name,
                   ghowner=ghowner, ghrepo=ghrepo,
                   channels=args.channels, queue=args.queue, sub_dir=args.sub_dir,
                   email=args.email)

    log.info("CI Added to package %s", args.package)

def add_parser(subparsers):

    description = 'Save build info to be triggered later'
    parser = subparsers.add_parser('save',
                                      help=description,
                                      description=description,
                                      epilog=__doc__,
                                      formatter_class=RawDescriptionHelpFormatter,
                                      )

    parser.add_argument('url',
                        help='The http github url to the repo')

    parser.add_argument('-p', '--package',
                       help="The binstar package namespace to upload the build to",
                       metavar='USER/PACKAGE',
                       type=package_specs)

    parser.add_argument('--sub-dir',
                       help="The sub directory within the git repository (github url submits only)")

    parser.add_argument('--channel', action='append', dest='channels',
                       help="Upload targets to this channel")

    parser.add_argument('--queue',
                       help="Build on this queue")

    parser.add_argument('--email', action='append',
                        help="Binstar usernames or email adresses to email when the build completes"
                        )

    parser.set_defaults(main=main)

