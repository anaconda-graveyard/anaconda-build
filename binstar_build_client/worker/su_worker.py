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
import shutil
import subprocess as sp

from binstar_client import errors

from binstar_build_client.utils.rm import rm_rf
from binstar_build_client.worker.worker import Worker
from binstar_build_client.worker.utils import process_wrappers
from binstar_build_client.worker.utils.build_log import BuildLog
from binstar_build_client.worker.utils.timeout import read_with_timeout

SU_WORKER_DEFAULT_PATH = '/opt/anaconda'

log = logging.getLogger('binstar.build')


def check_conda_path(build_user, python_install_dir):
    conda_exe = os.path.join(python_install_dir, 'bin', 'conda')
    check_conda = "{} && echo has_conda_installed".format(conda_exe)
    conda_output = sp.check_output(['su', '--login', '-c', check_conda, '-', build_user])
    if 'has_conda_installed' not in conda_output.decode().strip():
        raise errors.BinstarError('Did not find conda at {}'.format(conda_exe))
    return True


def test_su_as_user(build_user):
    whoami_as_user = sp.check_output(['su', '--login', '-c', 'whoami', '-', build_user])
    has_build_user = build_user in whoami_as_user.decode().strip()
    if not has_build_user:
        info = (build_user, whoami_as_user)
        raise errors.BinstarError('Cannot continue without build_user {}.'
                                  ' Got whoami = {}'.format(*info))
    return True


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
    is_root = os.getuid() == 0
    if not is_root:
        raise errors.BinstarError('Expected su_worker to run as root.')
    return test_su_as_user(build_user) and check_conda_path(build_user,
                                                            python_install_dir)


class SuWorker(Worker):
    '''Overrides the run method of Worker to run builds
    as a lesser user. '''

    def __init__(self, bs, worker_config, args):
        super(SuWorker, self).__init__(bs, worker_config, args)
        self.build_user = args.build_user
        self.python_install_dir = args.python_install_dir
        validate_su_worker(self.build_user, self.python_install_dir)


    def _finish_job(self, job_data, failed, status):
        '''Count job as finished, destroy build user processes,
        and replace build user's home directory'''
        self.destroy_user_procs()
        self.clean_home_dir()
        super(SuWorker, self)._finish_job(job_data, failed, status)


    def clean_home_dir(self):
        '''Delete lesser build_user's home dir and
        replace it with /etc/worker-skel'''
        home_dir = os.path.expanduser('~{}'.format(self.build_user))
        log.info('Remove build worker home directory: {}'.format(home_dir))
        rm_rf(home_dir)
        shutil.copytree('/etc/worker-skel', home_dir, symlinks=False)
        out = sp.check_output(['chown', '-R', "{}:{}".format(self.build_user, self.build_user), home_dir])
        if out:
            log.info(out)
        log.info('Copied /etc/worker-skel to {}.  Changed permissions.'.format(home_dir))

    def destroy_user_procs(self):
        log.info("Destroy {}'s processes".format(self.build_user))
        try:
            out = sp.check_output(['pkill', '-U', self.build_user])
        except sp.CalledProcessError as e:
            # the user has no processes running and pkill returns non-zero
            out = None
        if out:
            log.info(out)

    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None,
            build_was_stopped_by_user=lambda:None):

        log.info("Running build script")

        working_dir = self.working_dir(build_data)
        own_script = ['chown', '{}:{}'.format(self.build_user, self.build_user), os.path.abspath(script_filename)]
        log.info('Running: {}'.format(" ".join(own_script)))
        log.info(sp.check_output(own_script))

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
