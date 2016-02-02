import logging
import os
import psutil
import sys

from binstar_client import errors
from binstar_build_client.utils import get_conda_root_prefix

log = logging.getLogger('binstar.build')

def validate_procs():
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
        cmd = None
        try:
            cmd = proc.cmdline()
        except psutil.AccessDenied:
            continue
        except psutil.ZombieProcess:
            log.info('ZombieProcess: {} {}'.format(proc.pid, cmd))
        open_files = proc.open_files()
        msg = "Pid {} is running {} with open files {}"
        if cmd and cmd[0].strip().startswith(executable_dir):
            procs_on_wrong_python.append(msg.format(proc.pid, cmd, open_files))
        else:
            for f in open_files:
                if f.startswith(executable_dir):
                    procs_on_wrong_python.append(msg.format(proc.pid, cmd, open_files))
    return procs_on_wrong_python

def validate_procs_main():
    for msg in validate_procs():
        log.info(msg)