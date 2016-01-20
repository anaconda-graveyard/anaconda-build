"""
SuWorker in this module is a subclass of worker.worker for
the purpose of running a root python build process that does each
build as a lesser user, build_user, via su.  SuWorker must
be run as root with a root python install.
"""
from __future__ import print_function, absolute_import, unicode_literals

import io
import logging
import os
import pwd
import shutil
import subprocess as sp

from binstar_client import errors

from binstar_build_client.utils.rm import rm_rf
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.utils import process_wrappers
from binstar_build_client.worker.utils.build_log import BuildLog
from binstar_build_client.worker.utils.timeout import read_with_timeout
from binstar_build_client.worker.register import WorkerConfiguration


SU_WORKER_DEFAULT_PATH = '/opt/anaconda'

OK_SU_WORKER_FILENAME = '.su_worker'

log = logging.getLogger('binstar.build')



def validate_su_worker_home(build_user):
    home = os.path.expanduser('~{}'.format(build_user))
    su_worker_file = os.path.join(home, OK_SU_WORKER_FILENAME)
    is_ok = os.path.exists(su_worker_file)
    template = 'Caution: Expecting a file {0} to exist in {1}' + \
               '\n\tThe file {0} indicates approval for ' + \
               'deleting a user\'s home directory ' + \
               '\n\t(in this case {2}\'s home directory.)'
    if not is_ok:
        raise errors.BinstarError(template.format(
                                    OK_SU_WORKER_FILENAME,
                                    home,
                                    build_user))
    etc_su_worker_file = os.path.join('/etc/worker-skel', OK_SU_WORKER_FILENAME)
    is_ok = os.path.exists(etc_su_worker_file)
    if not is_ok:
        raise errors.BinstarError(template.format(OK_SU_WORKER_FILENAME,
                                                  '/etc/worker-skel',
                                                  build_user))
    return True

def check_conda_path(build_user, python_install_dir):
    if not os.access(python_install_dir, os.R_OK and os.W_OK and os.X_OK):
        raise errors.BinstarError('User root must have read, write, '
                                  'execute access to '
                                  'python_install_dir {}'.format(python_install_dir))
    conda_exe = os.path.join(python_install_dir, 'bin', 'conda')
    check_conda = "{} && echo has_conda_installed".format(conda_exe)
    conda_output = sp.check_output(['su', '-', build_user, '--login', '-c', check_conda])
    if 'has_conda_installed' not in conda_output.decode().strip():
        raise errors.BinstarError('Did not find conda at {}'.format(conda_exe))
    return True


def test_su_as_user(build_user):
    whoami_as_user = sp.check_output(['su', '-', build_user, '--login', '-c', 'whoami'])
    has_build_user = build_user in whoami_as_user.decode().strip()
    if not has_build_user:
        info = (build_user, whoami_as_user)
        raise errors.BinstarError('Cannot continue without build_user {}.'
                                  ' Got whoami = {}'.format(*info))
    return True


def is_build_user_running(build_user):
    workers_dir = WorkerConfiguration.REGISTERED_WORKERS_DIR
    if not os.path.exists(workers_dir):
        return False
    for worker_file in os.listdir(workers_dir):
        worker_file = os.path.join(workers_dir, worker_file)
        with open(worker_file) as f:
            contents = f.read()
            if '{} running'.format(build_user) in contents:
                raise errors.BinstarError('The file {0} indicates user'
                                          ' {1} may already be running a'
                                          ' build worker with su_run, '
                                          'with possible collisions.'
                                          '\n\tDelete {0} if '
                                          'this is incorrect, or'
                                          ' run with different lesser build user.'.format(
                                            worker_file,
                                            build_user))

    return False

def validate_su_worker(build_user, python_install_dir):
    '''Ensure su_worker is running as root, that there is a build worker, that
    /etc/worker-skel exists, and that conda is accessible to the build_user.'''
    if build_user == 'root':
        raise errors.BinstarError('Do NOT make root the build_user.  '
                                  'The home directory of build_user is DELETED.')
    has_etc_worker_skel = os.path.isdir('/etc/worker-skel')
    if not has_etc_worker_skel:
        raise errors.BinstarError('Expected /etc/worker-skel to exist and '
                                  'be a template for {}\'s'
                                  ' home directory'.format(build_user))
    if not hasattr(os, 'getuid') or os.name == 'nt':
        raise errors.BinstarError('SuWorker only runs as root and only on linux/unix')
    is_root = os.getuid() == 0
    if not is_root:
        raise errors.BinstarError('Expected su_worker to run as root.')
    ok1 = test_su_as_user(build_user) and check_conda_path(build_user,
                                                            python_install_dir)
    ok2 = validate_su_worker_home(build_user)

    return ok1 and ok2 and not is_build_user_running(build_user)

def create_build_worker(build_user):
    existing_users = [item.pw_name for item in pwd.getpwall()]
    if build_user in existing_users:
        log.info('Not creating build user {} (already exists)'.format(build_user))
    else:
        log.info('useradd -M {}'.format(build_user))
        try:
            sp.check_output(['which', 'useradd'])
        except Exception as e:
            log.info("Cannot useradd.  `which useradd` returns nothing.")
            raise
        try:
            sp.check_output(['useradd', '-M', build_user])
        except Exception as e:
            log.info('Failed on useradd -M {}.'.format(build_user))
            raise

class SuWorker(Worker):
    '''Overrides the run method of Worker to run builds
    as a lesser user. '''

    def __init__(self, bs, worker_config, args):
        super(SuWorker, self).__init__(bs, worker_config, args)
        self.build_user = args.build_user
        self.python_install_dir = args.python_install_dir
        validate_su_worker(self.build_user, self.python_install_dir)
        create_build_worker(args.build_user)
        self.clean_home_dir()
        self.rm_conda_lock()

    def _finish_job(self, job_data, failed, status):
        '''Count job as finished, destroy build user processes,
        and replace build user's home directory'''
        self.destroy_user_procs()
        self.clean_home_dir()
        self.rm_conda_lock()
        super(SuWorker, self)._finish_job(job_data, failed, status)

    def rm_conda_lock(self):
        dot_conda = os.path.join(os.path.expanduser("~" + self.build_user), '.conda')
        envs = os.path.join(dot_conda, 'envs')
        dot_pkgs = os.path.join(envs, '.pkgs')
        if os.path.exists(dot_pkgs):
            existing = os.listdir(dot_pkgs)
            to_delete = [os.path.join(dot_pkgs, f) for f in existing if '.conda_lock' in f]
            for f in to_delete:
                os.unlink(f)

    def clean_home_dir(self):
        '''Delete lesser build_user's home dir and
        replace it with /etc/worker-skel'''
        home_dir = os.path.expanduser('~{}'.format(self.build_user))
        log.info('Remove build worker home directory: {}'.format(home_dir))
        rm_rf(home_dir)
        shutil.copytree('/etc/worker-skel', home_dir, symlinks=False)
        out = sp.check_output(['chown', '-R', self.build_user, home_dir])
        if out:
            log.info(out)
        log.info('Copied /etc/worker-skel to {}.  Changed permissions.'.format(home_dir))

    def destroy_user_procs(self):
        log.info("Destroy {}'s processes".format(self.build_user))
        try:
            out = sp.check_output(['pkill', '-U', self.build_user])
        except sp.CalledProcessError as e:
            # the user has no processes running and pkill returns non-zero
            proc = sp.Popen(['ps', 'aux'], stdout=sp.PIPE)
            proc.wait()
            lines = []
            for line in proc.stdout.read().decode().splitlines():
                if line.startswith(self.build_user):
                    lines.append(line)
            if lines:
                log.warn('pkill was unable to kill all {} processes.'
                         '{} are still running'.format(self.build_user,
                                                       len(lines)))
                log.warn('Processes that should have been killed (ps aux output):')
                for line in lines:
                    log.warn(line)

    def build(self, job_data):
        self.clean_home_dir()
        self.rm_conda_lock()
        return super(SuWorker, self).build(job_data)

    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None,
            build_was_stopped_by_user=lambda:None):

        log.info("Running build script")

        working_dir = self.working_dir(build_data)
        own_script = ['chown', '-R', self.build_user, os.path.abspath(working_dir)]
        log.info('Running: {}'.format(" ".join(own_script)))
        log.info(sp.check_output(own_script))
        #   permissions = ['chmod', '-R', '0775', working_dir]
        #log.info('Running: {}'.format(permissions))
        #log.info(sp.check_output(permissions))
        args = [os.path.abspath(script_filename), '--api-token', api_token]

        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            args.extend(['--build-tarball', build_filename])

        log.info("Running command: (iotimeout={})".format(iotimeout))
        log.info(args)
        p0 = process_wrappers.SuBuildProcess(args, working_dir,
                                           self.build_user, self.args.site,
                                           self.python_install_dir)
        try:
            read_with_timeout(
                p0,
                build_log,
                timeout,
                iotimeout,
                BuildLog.INTERVAL,
                build_was_stopped_by_user
            )
        except BaseException:
            log.error(
                "Binstar build process caught an exception while waiting for the build to" "finish")
            p0.kill()
            p0.wait()
            raise
        return p0.poll()
