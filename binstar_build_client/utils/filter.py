
from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import os
from subprocess import check_output, CalledProcessError

class ExcludeGit(object):
    def __init__(self, path, use_git_ignore=True):
        self.path = os.path.abspath(path)
        try:
            filelist = check_output(['git', 'ls-files'], cwd=self.path).decode().split()
            self.to_include = [os.path.join(self.path, fn) for fn in filelist]
        except CalledProcessError as err:
            self.to_include = None

        self.num_included = 0

    def __call__(self, filename):
        if self.to_include is None:
            return False

        if os.path.isdir(filename):
            return False

        if filename in self.to_include:
            self.num_included += 1
            return False

        return True
