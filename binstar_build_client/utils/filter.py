'''
Created on May 8, 2014

@author: sean
'''

from fnmatch import fnmatch
import os

class ExcludeGit(object):
    def __init__(self, path, use_git_ignore=True):
        self.path = os.path.abspath(path)
        self.to_ignore = []
        while use_git_ignore:
            git_ignore = os.path.join(path, '.gitignore')
            if os.path.isfile(git_ignore):
                with open(git_ignore) as gi:

                    to_ignore = [line.strip() for line in gi if not line.startswith('#') if line.strip()]
                    self.to_ignore = ['**%s' % line if line[0] == '/' else '**/%s' % line for line in to_ignore]
                    self.to_ignore.extend(line + '/' for line in self.to_ignore if line[-1] != '/')
                break
            next_path = os.path.dirname(path)
            if next_path == path: break
            path = next_path

    def __call__(self, filename):
        if '/.git/' in filename:
            return True
        if not self.to_ignore:
            return False

        if os.path.isdir(filename):
            filename += '/'
        if filename.startswith(self.path):
            filename = filename[len(self.path):]

        return any(fnmatch(filename, pat) for pat in self.to_ignore)

