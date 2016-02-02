import logging
import os
import psutil
import sys

from binstar_client import errors
from binstar_build_client.utils import get_conda_root_prefix

log = logging.getLogger('binstar.build')

def validate_procs(ignore_process_check=False):
    '''Prevent windows workers from modifying their executable_dir,
    such as conda.exe'''
    if os.name != 'nt':
        return []
    procs_on_wrong_python = []
    executable_dir = sys.prefix
    my_pid = os.getpid()
    for proc in psutil.process_iter():
        if proc.pid == my_pid:
            continue
        exe = None
        try:
            exe = proc.exe()

        except psutil.AccessDenied:
            log.info('AccessDenied to proc with pid {}'.format(proc.pid))
            continue
        except psutil.ZombieProcess:
            log.info('ZombieProcess: {}'.format(proc.pid))
            continue
        open_files = ['Cannot check open_files()']
        try:
            if hasattr(proc, 'open_files'):
                open_files = proc.open_files()
        except psutil.AccessDenied:
            log.info('AccessDenied to open_files()'
                     ' from pid {}'.format(proc.pid))
            open_files = ['AccessDenied']
        msg = "Pid {} is running {} with open_files() :  {}"
        if exe and exe.strip().startswith(executable_dir):
            procs_on_wrong_python.append(msg.format(proc.pid, exe, open_files))
        else:
            for f in open_files:
                if f.startswith(executable_dir):
                    procs_on_wrong_python.append(msg.format(proc.pid, exe, open_files))
    if not ignore_process_check and procs_on_wrong_python:
        raise errors.BinstarError("There were processes running on the "
                          "incorrect "
                          "Python prefix: {}".format(" ".join(procs_on_wrong_python)))
    elif procs_on_wrong_python:
        log.info('There were processes '
                 'running on the incorrect '
                 'Python prefix: {}'.format(" ".join(procs_on_wrong_python)))

    return procs_on_wrong_python
