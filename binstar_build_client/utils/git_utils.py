from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import atexit
from logging import getLogger
import shutil

from six.moves.urllib.parse import urlparse, urlunparse
from binstar_client import errors
import re


log = getLogger('binstar.git')

def is_url(path):
    url = urlparse(path)
    if url.scheme:
        return True

def get_urlpath(path):
    url = urlparse(path)
    return url.path[1:]  # path is /a/b (want to remove first slash)



def clone_repo(path):
    url = urlparse(path)
    fragment = url.fragment
    scheme = url.scheme[4:]

    git_url = urlunparse((scheme, url.netloc, url.path, '', '', ''))
    import tempfile
    from subprocess import check_call
    tmp_dir = tempfile.mkdtemp('.git', 'binstar-build')
    log.info(' '.join(['git', 'clone', git_url, tmp_dir]))
    check_call(['git', 'clone', git_url, tmp_dir])
    log.info(' '.join(['git', 'checkout', fragment]))
    check_call(['git', 'checkout', fragment], cwd=tmp_dir)

    def rmrepo():
        log.info("Removing git temp git repo")
        shutil.rmtree(tmp_dir, ignore_errors=True)

    atexit.register(rmrepo)

    return tmp_dir


def get_gitrepo(url):
    # split branch from repo

    if url.netloc != 'github.com':
        raise errors.UserError("Currently only github.com urls are supported (got %s)" % url.netloc)

    pat = re.compile('^/(?P<repo>[\w-]+/[\w-]+)(/tree/(?P<branch>[\w/]+))?(.git)?$')
    match = pat.match(url.path)
    if not match:
        raise errors.UserError("URL path '%s' is not a git repo" % url.path)

    groups = match.groupdict()
    repo = groups.get('repo')
    branch = groups.get('branch') or url.fragment or 'master'
    builds = {'repo': repo, 'branch':branch}
    return builds
