import logging
import pipes
import psutil
import requests
import subprocess
import os
import signal

WIN_32 = os.name == 'nt'

if WIN_32:
    import win32job
    import pywintypes

from binstar_client.utils import get_config

log = logging.getLogger('binstar.build')


class DockerBuildProcess(object):
    def __init__(self, cli, cont):
        self.cli = cli
        self.cont = cont
        self.stream = self.cli.attach(cont, stream=True, stdout=True, stderr=True)
        self.pid = 'docker container'

    def kill(self):
        self.cli.kill(self.cont)

    def wait(self):
        return self.cli.wait(self.cont)

    def remove(self):
        self.cli.remove_container(self.cont, v=True)

    def readline(self):
        return next(self.stream, b'')

    def poll(self):
        try:
            return self.cli.wait(self.cont, timeout=0.1)
        except requests.exceptions.ReadTimeout:
            return None


def create_job(hProcess):
    hJob = win32job.CreateJobObject(None, "")
    extended_info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
    extended_info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, extended_info)
    win32job.AssignProcessToJobObject(hJob, hProcess)

    return hJob

class BuildProcess(subprocess.Popen):

    def __init__(self, args, cwd):

        if WIN_32:
            preexec_fn = None
        else:
            preexec_fn = os.setpgrp

        super(BuildProcess, self).__init__(args=args, cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=preexec_fn
        )

        if WIN_32:
            self.job = create_job(self._handle)
        else:
            self.job = None


    def kill_job(self):
        if self.job is None:
            return
        log.warning("Kill win32 JobObject handle: {0}".format(self.job))

        try:
            win32job.TerminateJobObject(self.job, 1)
        except pywintypes.error as err:
            log.warning("Could not terminate job object")
            log.warning(err)

    def kill_pg(self):

        if WIN_32:
            return
        try:
            pgid = os.getpgid(self.pid)
        except OSError as err:
            log.warning("Could not get process group for pid {}".format(self.pid))
            log.warning(err)
            return

        log.warning("Kill posix process group pgid: {0}".format(pgid))

        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError as err:
            log.warning("Could not kill process group for pid {}".format(self.pid))
            log.warning(err)

    def kill(self):
        '''Kill all processes and child processes'''

        try:
            log.warning("Kill Tree parent pid: {0}".format(self.pid))
            parent = psutil.Process(self.pid)
            children = parent.children(recursive=True)
        except psutil.NoSuchProcess:
            log.warning("Parent pid {0} is already dead".format(self.pid))
            # Already dead
            parent = None
            children = []

        self.kill_job()
        self.kill_pg()

        if parent and parent.is_running():
            log.info("BuildProcess.kill: parent pid {} is being killed".format(parent.pid))
            super(BuildProcess, self).kill()

        for child in children:
            if child.is_running():
                log.info("BuildProcess.kill: child pid {} is being killed".format(child.pid))
                child.kill()

    def readline(self):
        return self.stdout.readline()


class SuBuildProcess(BuildProcess):

    def __init__(self, args, cwd, build_user, site, python_install_dir):
        self.python_install_dir = python_install_dir
        self.build_user = build_user
        self.site = site
        args = " ".join(pipes.quote(arg) for arg in args)
        args = self.su_with_env(args)
        self.cwd = cwd
        super(SuBuildProcess, self).__init__(args, cwd)

    def kill(self):
        super(SuBuildProcess, self).__init__(['pkill',
                                              '-U',
                                              self.build_user],
                                                self.cwd)

    def su_with_env(self, cmd):
        '''args for su as build_user with the anaconda settings'''
        cmds = ['su', '-', self.build_user, '--login', '-c', self.source_env]
        cmds[-1] += " && anaconda config --set url {} && ".format(self.anaconda_url)
        cmds[-1] += " conda config --set always_yes true && "
        cmds[-1] += cmd
        return cmds

    @property
    def anaconda_url(self):
        config = get_config(remote_site=self.site)
        return config.get('url', 'https://api.anaconda.org')

    @property
    def source_env(self):
        return ("export PATH={0}/bin:${{PATH}}").format(self.python_install_dir)


