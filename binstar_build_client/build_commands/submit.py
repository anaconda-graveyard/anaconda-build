'''
Build command

Submit a build from your local path or  via a git url:

See also:

  * [Submit A Build](http://docs.anaconda.org/build.html#SubmitABuild)
  * [Submit A Build From Github](http://docs.anaconda.org/build.html#GithubBuilds)

'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from argparse import RawDescriptionHelpFormatter, Namespace
from contextlib import contextmanager
import logging
import os
from os.path import abspath, join, isfile
import tarfile
import tempfile

from binstar_build_client import BinstarBuildAPI
from binstar_build_client.utils import get_anaconda_url
from binstar_build_client.utils.filter import ExcludeGit
from binstar_build_client.utils.git_utils import is_url, get_urlpath, \
    get_gitrepo
from binstar_build_client.utils.matrix import serialize_builds, load_all_binstar_yml
from binstar_build_client.build_commands.info import tail
from binstar_client import errors
from binstar_client.errors import UserError
from binstar_client.utils import get_binstar, PackageSpec, upload_print_callback
from binstar_client.utils import package_specs
from six.moves.urllib.parse import urlparse

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

def submit_build(binstar, args):

    path = abspath(args.path)

    log.info('Getting build product: %s' % abspath(args.path))

    build_matrix = load_all_binstar_yml(path)
    builds = list(serialize_builds(build_matrix))

    if args.platform:

        log.info("Only selecting builds on platform %s" % args.platform)
        builds = [b for b in builds if b['platform'] == args.platform]

    if not builds:
        msg = "No build instructions found"
        if args.platform:
            msg += " for platform %s" % args.platform
        raise errors.BinstarError(msg)

    log.info('Submitting %i sub builds' % len(builds))
    for i, build in enumerate(builds):
        log.info(' %i)' % i + ' %(platform)-10s  %(engine)-15s  %(env)-15s' % build)

    if not args.dry_run:
        if args.git_url:
            log.info("Submitting the following repo for package creation: %s" % args.git_url)

        else:
            with mktemp() as tmp:
                log.info("Archiving build directory for upload ...")
                with tarfile.open(tmp, mode='w|bz2') as tf:
                    exclude = ExcludeGit(path, use_git_ignore=not args.dont_git_ignore)
                    tf.add(path, '.', exclude=exclude)

                log.info("Created archive (%i files); Uploading to Anaconda Build service" % exclude.num_included)
                queue_tags = []
                if args.buildhost:
                    queue_tags.append('hostname:%s' % args.buildhost)

                if args.dist:
                    queue_tags.append('dist:%s' % args.dist)

                with open(tmp, mode='rb') as fd:

                    # TODO: change channels= to labels=
                    build = binstar.submit_for_build(args.package.user, args.package.name, fd, builds,
                                                     channels=args.labels,
                                                     queue=args.queue, queue_tags=queue_tags,
                                                     test_only=args.test_only, callback=upload_print_callback(args))

                if args.tail:
                    tail_sub_build(binstar, args, build['build_no'])
                else:
                    print_build_results(args, build, binstar)
    else:
        log.info('Build not submitted (dry-run)')


def print_build_results(args, build, binstar):

    log.info('')
    build_result_url = build.get('url')
    if not build_result_url:
        build_result_url = get_anaconda_url(binstar, '/{package.user}/{package.name}/builds/matrix/{build_no}'.format(
            package=args.package,
            build_no=build['build_no'],
        ))
    log.info('To view this build go to %s' % build_result_url)
    log.info('')
    log.info('You may also run\n\n    anaconda build tail -f %s/%s %s\n' % (args.package.user, args.package.name, build['build_no']))
    log.info('')
    log.info('Build %s submitted' % build['build_no'])

def submit_git_build(binstar, args):

    log.info("Submitting the following repo for package creation: %s" % args.git_url)
    builds = get_gitrepo(urlparse(args.git_url))

    if not args.package:
        user = binstar.user()
        user_name = user['login']
        package_name = builds['repo'].split('/')[1]
        log.info("Using repo name '%s' as the pkg name." % package_name)
        args.package = PackageSpec(user_name, package_name)

    try:
        _ = binstar.package(args.package.user, args.package.name)
    except errors.NotFound:
        raise errors.UserError("Package %s does not exist" % (args.package,))


    if not args.dry_run:
        log.info("Submitting the following repo for package creation: %s" % args.git_url)
        builds = get_gitrepo(urlparse(args.path))
        # TODO: change channels= to labels=
        build = binstar.submit_for_url_build(args.package.user, args.package.name, builds,
                                             channels=args.labels, queue=args.queue, sub_dir=args.sub_dir,
                                             test_only=args.test_only, callback=upload_print_callback(args),
                                             filter_platform=args.platform,
                                                )

        if args.tail:
            tail_sub_build(binstar, args, build['build_no'])
        else:
            print_build_results(args, build, binstar)
    else:
        log.info('Build not submitted (dry-run)')

def sub_build_gen(binstar, username, package, build_no):
    for build in binstar.builds(username, package, build_no):
        for item in build['items']:
            yield build['build_no'], item['sub_build_no']



def tail_sub_build(binstar, args, build_no):
    spacer = '###\n###'
    for build_no, sub_build_no in sub_build_gen(binstar, args.package.user,
                                                args.package.name, build_no):
        build_str = '{}.{}'.format(build_no, sub_build_no)
        log.info(spacer)
        log.info('###\t\tanaconda build tail -f {}/{} {}'.format(args.package.user,
                                                                 args.package.name,
                                                                 build_str))
        log.info(spacer)
        ret_val = tail(args.package.user, args.package.name,
                       build_str, follow=True, limit=None,
                       binstar=binstar)
        if ret_val:
            return ret_val
    return 0

def clean_validate_tail_args(args):
    if args.tail or args.sub_builds:
        args.tail = True

def main(args):
    binstar = get_binstar(args, cls=BinstarBuildAPI)
    package_name = None
    user_name = None
    if args.git_url:
        args.path = args.git_url

    if args.git_url or is_url(args.path):
        args.git_url = args.path
        args.git_url_path = get_urlpath(args.path)
        args.dont_git_ignore = True

        submit_git_build(binstar, args)


    # not a github repo (must check for valid .binstar.yml file
    else:
        binstar_yml = join(args.path, '.binstar.yml')

        if not isfile(binstar_yml):
            raise UserError("file %s does not exist\n perhaps you should run\n\n    anaconda build init\n" % binstar_yml)

        package_name = None
        user_name = None
        build_matrix = load_all_binstar_yml(args.path)
        for build in build_matrix:
            if build.get('package'):
                package_name = build.get('package')
            if build.get('user'):
                user_name = build.get('user')

        # Force package to exist
        if args.package:
            if user_name and not args.package.user == user_name:
                log.warn('User name does not match the user specified in the .binstar.yml file (%s != %s)', args.package.user, user_name)
            user_name = args.package.user
            if package_name and not args.package.name == package_name:
                log.warn('Package name does not match the user specified in the .binstar.yml file (%s != %s)', args.package.name, package_name)
            package_name = args.package.name
        else:
            if user_name is None:
                user = binstar.user()
                user_name = user['login']
            if not package_name:
                raise UserError("You must specify the package name in the .binstar.yml file or the command line")

        try:
            _ = binstar.package(user_name, package_name)
        except errors.NotFound:
            log.error("The package %s/%s does not exist." % (user_name, package_name))
            log.error("Run: \n\n    anaconda package --create %s/%s\n\n to create this package" % (user_name, package_name))
            raise errors.NotFound('Package %s/%s' % (user_name, package_name))
        args.package = PackageSpec(user_name, package_name)

        submit_build(binstar, args)

def add_tail_parser(parser):
    tail_group = parser.add_argument_group('tail')
    tail_group.add_argument('--tail',
                            '-f',
                            action='store_true',
                            dest='tail',
                            help="Do 'tail -f on each sub-build log or "
                                 "each of the sub-builds given in '--sub-builds'")
    tail_group.add_argument('--sub-builds',
                            '-s',
                            type=int,
                            nargs="+",
                            action='append',
                            help="If --tail or -f is given, "
                                 "then tail sub-builds in '--sub-builds <int> <int>' "
                                 " \n\tOtherwise with --tail or -f, tail -f all sub-builds")


def add_parser(subparsers):
    description = 'Submit a directory or github repo for building'
    parser = subparsers.add_parser('submit',
                                   help=description, description=description,
                                   epilog=__doc__,
                                   formatter_class=RawDescriptionHelpFormatter,
                                   )

    parser.add_argument('path', default='.', nargs='?',
                        help='filepath or github url to submit')

    parser.add_argument('--git-url',
                       help="The github url with valid .binstar.yml file to clone")

    parser.add_argument('-n', '--dry-run',
                       help="Parse the build file but don't submit", action='store_true')

    parser.add_argument('--no-progress',
                       help="Don't show progress bar", action='store_true')

    parser.add_argument('--dont-git-ignore',
                       help="Don't ignore files from .gitignore", action='store_true')


    fgroup = parser.add_argument_group('filters')

    fgroup.add_argument('--buildhost',
                        help="The host name of the intended build worker")

    fgroup.add_argument('--dist',
                        help=("The os distribution of intended build worker (e.g centos, ubuntu) "
                              "Use 'anaconda build queue' to view the workers")
                        )

    fgroup.add_argument('--platform',
                        help=("The platform to run (e.g linux-64, win-64, osx-64, etc) "
                              "(default: all the platforms in the .binstar.yaml file)")
                        )

    cgroup = parser.add_argument_group('build control')
    parser.add_argument('--queue',
                       help="Build on this queue")

    cgroup.add_argument('--channel', action='append', dest='labels',
                       help="[DEPRECATED] Upload targets to this channel")
    cgroup.add_argument('--label', action='append', dest='labels',
                       help="Upload targets to this label")
    cgroup.add_argument('--test-only', '--no-upload', action='store_true',
                        dest='test_only',
                        help="Don't upload the build targets to Anaconda Cloud, but run everything else")
    cgroup.add_argument('-p', '--package',
                       help="The Anaconda Cloud package namespace to upload the build to",
                       metavar='USER/PACKAGE',
                       type=package_specs)

    cgroup.add_argument('--sub-dir',
                       help="The sub directory within the git repository (github url submits only)")

    add_tail_parser(parser)
    parser.set_defaults(main=main)
