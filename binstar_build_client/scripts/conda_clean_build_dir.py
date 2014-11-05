"""
Remove all conda build artifacts
"""

from __future__ import print_function
import shutil
from argparse import ArgumentParser
import os
from binstar_build_client.utils import get_conda_root_prefix
from os.path import islink, isfile, isdir
import subprocess
import time
import sys
import stat

def rm_rf(path, max_retries=5):
    """
    Completely delete path
    max_retries is the number of times to retry on failure. The default is
    5. This only applies to deleting a directory.
    """
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        os.unlink(path)

    elif isdir(path):
        for i in range(max_retries):
            try:
                shutil.rmtree(path)
                return
            except OSError as e:
                msg = "Unable to delete %s\n%s\n" % (path, e)
                if sys.platform == 'win32':
                    try:
                        def remove_readonly(func, path, excinfo):
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        shutil.rmtree(path, onerror=remove_readonly)
                        return
                    except OSError as e1:
                        msg += "Retry with onerror failed (%s)\n" % e1

                    try:
                        subprocess.check_call(['cmd', '/c', 'rd', '/s', '/q', path])
                        return
                    except subprocess.CalledProcessError as e2:
                        msg += '%s\n' % e2
                print(msg + "Retrying after %s seconds..." % i)
                time.sleep(i)

        # Final time. pass exceptions to caller.
        shutil.rmtree(path)

def main():
    parser = ArgumentParser(description=__doc__)
    parser.parse_args()

    root_env = get_conda_root_prefix()
    build_root = os.path.join(root_env, 'conda-bld')
    if os.path.isdir(build_root):
        print("Removing conda build root %s" % build_root)
        rm_rf(build_root)
    else:
        print("Conda build root %s does not exist" % build_root)


if __name__ == '__main__':
    main()
