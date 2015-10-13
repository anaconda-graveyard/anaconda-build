'''

'''

from argparse import RawDescriptionHelpFormatter, FileType
from binstar_client.utils import package_specs, get_binstar
from binstar_build_client import BinstarBuildAPI

def main(args):
    bs = get_binstar(args, BinstarBuildAPI)

    if  '.' in args.build:
        major, minor = args.build.split('.', 1)
    else:
        major, minor = args.build, 0

    major, minor = int(major), int(minor)

    bs.upload_test_results(args.action, args.package.user, args.package.name,
                           major, minor, args.filename,
                           )

def add_parser(subparsers):

    description = '[Advanced] Attach results to build'
    parser = subparsers.add_parser('results',
                                      help=description,
                                      description=description,
                                      epilog=__doc__,
                                      formatter_class=RawDescriptionHelpFormatter
                                      )
    # ArgumentParser.add_subparsers(self)
    parser.add_argument('action',
                   choices=['testsuite', 'summary'])

    parser.add_argument('package',
                   metavar='USER/PACKAGE',
                   type=package_specs)
    parser.add_argument('build', metavar='MAJOR.MINOR')
    parser.add_argument('filename', type=FileType('r'))

    parser.set_defaults(main=main)
