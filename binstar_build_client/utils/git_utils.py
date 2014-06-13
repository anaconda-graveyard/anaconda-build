'''
Created on May 15, 2014

@author: sean
'''
from urlparse import urlparse, urlunparse
from logging import getLogger
import shutil
import atexit
log = getLogger('binstar.git')
def is_giturl(path):
    url = urlparse(path)
    print 'is_giturl', url
    if url.scheme and url.scheme.startswith('git+'):
        return True

def get_urlpath(path):
    url = urlparse(path)
    return url.path[1:] #path is /a/b (want to remove first slash)



def clone_repo(path):
    url = urlparse(path)
    fragment = url.fragment
    scheme = url.scheme[4:]

    git_url = urlunparse((scheme, url.netloc, url.path, '', '', ''))
    print "clone_repo!", git_url
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


