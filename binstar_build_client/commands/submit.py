'''
Build command
  
Submit a build:

    binstar-build submit [path]
    
You may also submit a build via a git url:

     binstar-build submit git+<git-url>[#branch]

    For example if I have the git repo https://github.com/srossross/testci:
        
        binstar-build submit git+https://github.com/srossross/testci
        
    Or to test a branch:
    
        binstar-build submit git+https://github.com/srossross/testci#feature/testing
     
See also:

    binstar-build tail -h
    
'''

from binstar_client.utils import get_binstar, PackageSpec, upload_print_callback
import logging, yaml
from os.path import abspath, join, isfile
from binstar_client.errors import UserError
import tempfile
import tarfile
from contextlib import contextmanager
import os
from binstar_client.utils import package_specs
from binstar_client import errors
from binstar_build_client import BinstarBuildAPI
from binstar_build_client.utils.matrix import serialize_builds
from binstar_build_client.utils.filter import ExcludeGit
from binstar_build_client.utils.git_utils import is_giturl, clone_repo

log = logging.getLogger('binstar.build')

@contextmanager
def mktemp(suffix=".tar.gz", prefix='binstar', dir=None):
    tmp = tempfile.mktemp(suffix, prefix, dir)
    log.debug('Creating temp file: %s' % tmp)
    try:
        yield tmp
    finally:
        log.debug('Removing temp file: %s' % tmp)
        os.unlink(tmp)

def submit_build(args):

    binstar = get_binstar(args, cls=BinstarBuildAPI)

    path = abspath(args.path)

    log.info('Getting build product: %s' % abspath(args.path))

    with open(join(path, '.binstar.yml')) as cfg:
        build_matrix = list(yaml.load_all(cfg))

    builds = list(serialize_builds(build_matrix))
    log.info('Submitting %i sub builds' % len(builds))
    for i, build in enumerate(builds):
        log.info(' %i)' % i + ' %(platform)-10s  %(engine)-15s  %(env)-15s' % build)

    if not args.dry_run:
        with mktemp() as tmp:
            log.info("Archiving build directory for upload")
            with tarfile.open(tmp, mode='w|bz2') as tf:
                tf.add(path, '.', exclude=ExcludeGit(path))

            log.info("Created archive uploading to binstar")
            with open(tmp, mode='rb') as fd:

                build_no = binstar.submit_for_build(args.package.user, args.package.name, fd, builds,
                                                    test_only=args.test_only, callback=upload_print_callback(args))

        log.info('')
        log.info('To view this build go to http://alpha.binstar.org/%s/%s/builds/matrix/%s' % (args.package.user, args.package.name, build_no))
        log.info('')
        log.info('You may also run\n\n    binstar-build tail -f %s/%s %s\n' % (args.package.user, args.package.name, build_no))
        log.info('')
        log.info('Build %s submitted' % build_no)

    else:
        log.info('Build not submitted (dry-run)')


def main(args):

    binstar = get_binstar(args, cls=BinstarBuildAPI)

    # Force user auth
    user = binstar.user()

    package_name = None
    user_name = None

    if is_giturl(args.path):
        args.path = clone_repo(args.path)


    binstar_yml = join(args.path, '.binstar.yml')

    if not isfile(binstar_yml):
        raise UserError("file %s does not exist\n perhaps you should run\n\n    binstar-build init\n" % binstar_yml)

    with open(binstar_yml) as cfg:
        for build in yaml.load_all(cfg):
            package_name = build.get('package')
            user_name = build.get('user')

    # Force package to exist
    if args.package:
        if user_name and not args.package.user == user_name:
            log.warn('User name does not match the user specified in the .bisntar.yml file (%s != %s)', args.package.user, user_name)
        user_name = args.package.user
        if package_name and not args.package.name == package_name:
            log.warn('Package name does not match the user specified in the .bisntar.yml file (%s != %s)', args.package.name, package_name)
        package_name = args.package.name
    else:
        if user_name is None:
            user_name = user['login']
        if not package_name:
            raise UserError("You must specify the package name in the .bisntar.yml file or the command line")

    try:
        _ = binstar.package(user_name, package_name)
    except errors.NotFound:
        log.error("The package %s/%s does not exist." % (user_name, package_name))
        log.error("Run: \n\n    binstar package --create %s/%s\n\n to create this package" % (user_name, package_name))
        raise errors.NotFound('Package %s/%s' % (user_name, package_name))
    args.package = PackageSpec(user_name, package_name)

    submit_build(args)

def add_parser(subparsers):
    parser = subparsers.add_parser('submit',
                                      help='Submit for building',
                                      description=__doc__,
                                      )

    parser.add_argument('path', default='.', nargs='?')

    parser.add_argument('--test-only', '--no-upload', action='store_true',
                        dest='test_only',
                        help="Don't upload the build targets to binstar, but run everything else")

    parser.add_argument('-p', '--package',
                       help="The binstar package namespace to upload the build to",
                       type=package_specs)

    parser.add_argument('-n', '--dry-run',
                       help="Parse the build file but don't submit", action='store_true')

    parser.add_argument('--no-progress',
                       help="Don't show progress bar", action='store_true')

    parser.set_defaults(main=main)

