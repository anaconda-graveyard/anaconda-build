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



class SuWorker(Worker):
    """
    
    """
    STATE_FILE = 'worker.yaml'
    JOURNAL_FILE = 'journal.csv'
    SLEEP_TIME = 10
    source_env = "export PATH=/opt/anaconda/bin:${PATH} "+ \
                "&& source activate anaconda.org "
        
    def __init__(self, bs, args, build_users):
        self.bs = bs
        self.args = args
        self.build_users = build_users
        self.busy = {key:False for key in self.build_users}
        
    def _handle_job(self, job_data):
        """
        Handle a single build job, running 
        it as a build_user.
        only catches build script level errors
        """

        try:
            build_user = []
            waits = 0
            while not len(build_user):
                build_user = [key for key in self.busy if not self.busy[key]]
                time.sleep(.2)
                waits += 1
                if waits % 100 == 0:
                    log.info('Wait for build user %d times' % waits)
            build_user = build_user[0]
            self.busy[build_user] = True
            args_to_build_worker = pickle.dumps([build_user, job_data, self.__dict__])
            self.clean_home_dir(build_user)
            self.destroy_user_procs(build_user)
            tmp_file = NamedTemporaryFile(delete=False,dir='/home/%s' % build_user)
            tmp_file.write(args_to_build_worker)
            tmp_file.close()

            self.cmd(['chown',"%s:%s" % (build_user, build_user), tmp_file.name])
            self.check_su(build_user)
            log.info('Build is being sent to user: %s' % build_user)
            build_subproc = "anaconda build build_subprocess %s" % tmp_file.name
            out = self.su_with_env(build_subproc, build_user)
            failed, status = json.load(open(out.split('BUILD_RESULTS_FILE:')[-1].strip()))
        except Exception as err:
            # Catch all exceptions here and submit a build error
            log.exception(err)
            failed = True
            status = 'error'
        except BaseException as err:
            # Catch all exceptions here and submit a build error
            log.exception(err)
            failed = True
            status = 'error'
            self._finish_job(job_data, failed, status, build_user)
            raise

        self._finish_job(job_data, failed, status, build_user)
 

    def _finish_job(self, job_data, failed, status, build_user):
        self.destroy_user_procs(build_user)
        self.clean_home_dir(build_user)
        Worker._finish_job(self, job_data, failed, status)
        self.busy[build_user] = False

    @property
    def anaconda_url(self):
        config = get_config(remote_site=self.args.site)
        return config.get('url', 'https://api.anaconda.org')
 
    def su_with_env(self, cmd, as_user):
        
        cmds = ['su','--login', '-c', self.source_env]
        cmds[-1] += (" && anaconda config --set url %s && " % self.anaconda_url) 
        cmds[-1] += cmd
        cmds += ['-', as_user] 
        return self.cmd(cmds)       
        
    def check_su(self, as_user):
        whoami = self.cmd(['su','--login','-c','whoami','-', as_user]).strip()
        if not as_user == whoami.strip():
            raise errors.BinstarError("Cannot su - in as %r. %r" % (as_user, whoami))
    def cmd(self, cmd):
        stdout = io.StringIO()
        proc = BufferedPopen(cmd, stdout=stdout)
        lines = []
        old_content =''
        while proc.poll() is None:
            content = stdout.getvalue()
            new_content = content[len(old_content)-1:].strip()
            if new_content:
                log.info(new_content)
            old_content = content 

        return stdout.getvalue()
    
    def clean_home_dir(self, as_user):
        home_dir = self.cmd(['su', '--login', '-c', 'pwd', '-', as_user]).strip()
        log.info('Remove build worker home directory of %s' % home_dir)
        out = self.cmd(['rm','-rf',home_dir])
        if out:
            log.info(out)
        shutil.copytree('/etc/worker-skel', home_dir, symlinks=False)
        self.cmd(['chown','-R', "%s:%s" % (as_user,as_user), home_dir])
        
    
    def destroy_user_procs(self, as_user):
        log.info("Destroy %s's processes" % as_user)
        out = self.cmd(['pkill','-U', as_user])
        if out:
            log.info(out)
 
