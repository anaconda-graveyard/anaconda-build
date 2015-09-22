"""
Remove all conda build artifacts
"""

from __future__ import print_function

from argparse import ArgumentParser
import os

from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.utils.rm import rm_rf


def main():
    parser = ArgumentParser(description=__doc__)
    parser.parse_args()

    root_env = get_conda_root_prefix()
    build_root = os.path.join(root_env, 'conda-bld')
    has_access = os.access(build_root, os.W_OK)
    if os.path.isdir(build_root) and has_access:
        print("Removing conda build root %s" % build_root)
        rm_rf(build_root)
    elif not os.path.isdir(build_root):
        print("Conda build root %s does not exist" % build_root)
    elif not has_access:
        print("No access to remove build root %s" % build_root)

if __name__ == '__main__':
    main()
