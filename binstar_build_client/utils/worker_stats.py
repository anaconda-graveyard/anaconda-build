'''
worker_stats.py - Gather info on workers' storage, memory, and
software installed.
'''
from __future__ import print_function
import json
import os
from subprocess import check_output as _check_output

from binstar_client import errors


def check_output(args, cwd='.', raise_=True):
    try:
        return _check_output(args, cwd=cwd, env=os.environ).decode()
    except Exception as e:
        if raise_:
            raise errors.BinstarError('Failed on {}'.format(args))

def storage_stats():
    if os.name == 'nt':
        disk_args = ['cmd', '/c', 'wmic', 'logicaldisk', 'get',
                       'size,freespace,caption,description,volumename']
        disk = check_output(disk_args)
        return {'logicaldisk': {'cmd': " ".join(disk_args),
                                'out': disk,
        }}
    else:
        return {'df': {'cmd': 'df', 'out': check_output(['df'])}}

def memory_stats():
    out = {}
    if os.name == 'nt':
        out['systeminfo'] = {'out': check_output(['systeminfo']),
                             'cmd': 'systeminfo'}
    else:
        meminfo = os.path.join('/', 'proc', 'meminfo')
        if os.path.exists(meminfo):
            out['meminfo'] = {'out': check_output(['cat', meminfo]),
                              'cmd': 'cat /proc/meminfo',}
        which_vm_stat = check_output(['which', 'vm_stat'], raise_=False)
        if which_vm_stat:
            out['vm_stat'] = {'out': check_output(['vm_stat']),
                              'cmd': 'vm_stat'}

    return out

def conda_stats():
    out = {}
    args = ['conda', 'list', '--json']
    conda_list = json.loads(check_output(args))
    out['conda list'] = {'out': conda_list, 'cmd': " ".join(args)}
    out['conda env list'] = {'out': json.loads(check_output(['conda','env', 'list', '--json'])),
                             'cmd': 'conda env list --json'}
    out['conda info'] = {'out': json.loads(check_output(['conda', 'info', '--json'])),
                         'cmd': 'conda info --json'}
    return out

def system_packages():
    out = {}
    if os.name != 'nt':
        args = ['apt', '--installed', 'list']
        apt_installed = check_output(args, raise_=False)
        if apt_installed:
            out['apt'] = {'cmd': ' '.join(args),
                          'out': apt_installed,}
        args = ['dpkg', '-l']
        dpkg = check_output(args, raise_=False)
        if dpkg:
            out['dpkg'] = {'out': dpkg,
                           'cmd': ' '.join(args),}
        args = ['brew', 'list']
        brew = check_output(args, raise_=False)
        if brew:
            out['brew'] = {'out': brew,
                           'cmd': ' '.join(args)}
        args = ['yum', 'list', 'installed']
        yum = check_output(args, raise_=False)
        if yum:
            out['yum'] = {'out': yum,
                          'cmd': ' '.join(args)}
    return out


def worker_stats():
    out = {}
    for func in (conda_stats, storage_stats,
                 memory_stats, system_packages):
        out.update(func())
    return out

