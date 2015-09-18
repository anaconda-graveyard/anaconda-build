"""
The worker 
"""
from __future__ import print_function, absolute_import, unicode_literals

from contextlib import contextmanager
import logging
import os
import time
import io
from binstar_build_client.utils.rm import rm_rf
from binstar_client import errors
import psutil
import requests
import yaml
import json
import pickle
import shutil
import sys
from tempfile import NamedTemporaryFile
from .utils.buffered_io import BufferedPopen
from .utils.build_log import BuildLog
from .utils.script_generator import gen_build_script, \
    EXIT_CODE_OK, EXIT_CODE_ERROR, EXIT_CODE_FAILED
from .worker import Worker
import inspect
from binstar_client.utils import get_config

log = logging.getLogger('binstar.build')

def get_my_procs():

    this_proc = psutil.Process()

    if os.name == 'nt':
        myusername = this_proc.username()
        def ismyproc(proc):
            try:
                return proc.username() == myusername
            except psutil.AccessDenied:
                return False
    else:
        def ismyproc(proc):
            if inspect.isroutine(this_proc.uids):
                # psutil >= 2
                return proc.uids().real == this_proc.uids().real
            else:
                # psutil < 2
                return proc.uids.real == this_proc.uids.real


    return {proc.pid for proc in psutil.process_iter() if ismyproc(proc)}

@contextmanager
def remove_files_after(files):
    try:
        yield
    finally:
        for filename in files:
            if os.path.isfile(filename):
                os.unlink(filename)
def cmd(cmd):
    stdout = io.StringIO()
    proc = BufferedPopen(cmd, stdout=stdout)
    proc.wait()
    return stdout.getvalue()

is_root = 'root' in cmd(['whoami']).strip()
is_root_install = '/opt/anaconda' in sys.prefix
has_etc_worker_skel = os.path.isdir('/etc/worker-skel')

def validate_su_worker(build_user):
    if not is_root:
        raise errors.BinstarError('su_worker must be run as root. Got %r' % is_root)
    if not is_root_install:
        raise errors.BinstarError('python must be in /opt/anaconda for su_worker')
    if not has_etc_worker_skel:
        raise errors.BinstarError('Cannot continue su_worker without /etc/worker-skel,' +\
                                      'a template for new build user home directory.')
    whoami_as_user = cmd(['su','--login','-c','whoami', '-', build_user]).strip()
    has_build_user = build_user in whoami_as_user
    if not has_build_user:
        info = (build_user, whoami_as_user)
        raise errors.BinstarError('Cannot continue without build_user %r. Got whoami = %r' % info)
    return True
class SuWorker(Worker):
    """
    
    """
    STATE_FILE = 'worker.yaml'
    JOURNAL_FILE = 'journal.csv'
    SLEEP_TIME = 10
    source_env = "export PATH=/opt/anaconda/bin:${PATH} "+ \
                "&& source activate anaconda.org "
    
    def __init__(self, bs, args, build_user):
        super(SuWorker, self).__init__(bs, args)
        self.build_user = build_user
        validate_su_worker(self.build_user)

    def _finish_job(self, job_data, failed, status):
        '''Count job as finished, destroy build user processes,
        and replace build user's home directory'''
        self.destroy_user_procs()
        self.clean_home_dir()
        self.rm_rf_conda_bld()
        super(SuWorker, self)._finish_job(job_data, failed, status)

    @property
    def anaconda_url(self):
        config = get_config(remote_site=self.args.site)
        return config.get('url', 'https://api.anaconda.org')
 
    def su_with_env(self, cmd):
        '''args for su as build_user with the right anaconda settings'''
        cmds = ['su','--login', '-c', self.source_env]
        cmds[-1] += (" && anaconda config --set url %s && " % self.anaconda_url) 
        cmds[-1] += cmd
        cmds += ['-', self.build_user] 
        return cmds       
        
    def clean_home_dir(self):
        
        home_dir = cmd(['su', '--login', '-c', 'pwd', '-', self.build_user]).strip()
        log.info('Remove build worker home directory: %s' % home_dir)
        rm_rf(home_dir)
        shutil.copytree('/etc/worker-skel', home_dir, symlinks=False)
        out = cmd(['chown','-R', "%s:%s" % (self.build_user, self.build_user), home_dir])
        if out:
            log.info(out)
        log.info('Copied /etc/worker-skel to %s.  Changed permissions.' % home_dir)
        self.rm_rf_conda_bld()

    def rm_rf_conda_bld(self):
        '''build user is unable to do conda-clean-build-dir for 
        lack of permissions to the root directory /opt/anaconda/conda-bld, 
        This removes that dir by root user instead.'''
        rm_rf('/opt/anaconda/conda-bld')

    def destroy_user_procs(self):
        log.info("Destroy %s's processes" % self.build_user)
        out = cmd(['pkill','-U', self.build_user])
        if out:
            log.info(out)
 
    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None):

        self.rm_rf_conda_bld()

        log.info("Running build script")

        working_dir = self.working_dir(build_data)

        args = [os.path.abspath(script_filename), '--api-token', api_token]


        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            args.extend(['--build-tarball', build_filename])

        log.info("Running command: (iotimeout=%s)" % iotimeout)
        log.info(" ".join(args))

        if self.args.show_new_procs:
            already_running_procs = get_my_procs()
        args = self.su_with_env(" ".join(args))
        p0 = BufferedPopen(args, stdout=build_log, iotimeout=iotimeout, cwd=working_dir)

        try:
            exit_code = p0.wait()
        except BaseException:
            log.error("Binstar build process caught an exception while waiting for the build to finish")
            p0.kill_tree()
            p0.wait()
            raise
        finally:
            if self.args.show_new_procs:
                currently_running_procs = get_my_procs()
                new_procs = [psutil.Process(pid) for pid in currently_running_procs - already_running_procs]
                if new_procs:
                    build_log.write("WARNING: There are processes that were started during the build and are still running\n")
                    for proc in new_procs:
                        build_log.write(" - Process name:%s pid:%s\n" % (proc.name, proc.pid))
                        try:
                            cmdline = ' '.join(proc.cmdline)
                        except:
                            pass
                        else:
                            build_log.write("    + %s\n" % cmdline)
            if p0.stdout and not p0.stdout.closed:
                log.info("Closing subprocess stdout PIPE")
                p0.stdout.close()


        return exit_code
