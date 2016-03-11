import logging
import psutil
import requests
import subprocess
import os
import signal

from binstar_build_client.worker.utils.generator_file import GeneratorFile

WIN = os.name == 'nt'

if WIN:
    import win32job
    import pywintypes

log = logging.getLogger('binstar.build')


class DockerBuildProcess(object):
    def __init__(self, cli, cont):
        self.cli = cli
        self.cont = cont
        self.stdout = GeneratorFile(self.cli.attach(cont, stream=True, stdout=True, stderr=True))
        self.pid = 'docker container'

    def kill(self):
        try:
            self.cli.kill(self.cont)
        except requests.HTTPError:
            log.warn('Could not kill docker process', exc_info=True)

    def wait(self):
        return self.cli.wait(self.cont)

    def remove(self):
        self.cli.remove_container(self.cont, v=True)

    def poll(self):
        try:
            return self.cli.wait(self.cont, timeout=0.1)
        except requests.exceptions.ReadTimeout:
            return None


def create_job(hProcess):
    '''
    create_job(hProcess) creates win32job with correct flags:

    Note on JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
        https://msdn.microsoft.com/en-us/library/windows/desktop/ms684161(v=vs.85).aspx
        However, if the job has the
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE flag specified,
        closing the last job object handle terminates all
        associated processes and then destroys the job
        object itself.
    '''
    hJob = win32job.CreateJobObject(None, "")
    extended_info = win32job.QueryInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation)
    extended_info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(hJob, win32job.JobObjectExtendedLimitInformation, extended_info)
    win32job.AssignProcessToJobObject(hJob, hProcess)

    return hJob

class BuildProcess(subprocess.Popen):

    def __init__(self, args, cwd):

        if WIN:
            preexec_fn = None
        else:
            preexec_fn = os.setpgrp

        super(BuildProcess, self).__init__(args=args, cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=preexec_fn
        )

        if WIN:
            self.job = create_job(self._handle)
        else:
            self.job = None


    def kill_job(self):
        ''' kill_job is for windows only'''
        if not WIN:
            return
        log.info("Kill Windows JobObject handle: {0}".format(self.job))

        try:
            win32job.TerminateJobObject(self.job, 1)
        except pywintypes.error as err:
            log.warning("Could not terminate job object")
            log.warning(err)
            return err

    def kill_pg(self):
        '''kill_pg is for posix only '''
        if WIN:
            return

        try:
            pgid = os.getpgid(self.pid)
        except OSError as err:
            log.warning("Could not get process group for pid %s", self.pid, exc_info=err)
            return err

        log.info("Kill posix process group pgid: {0}".format(pgid))

        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError as err:
            log.warning("Could not kill process group for pid {}".format(self.pid), exc_info=err)
            return err

    def kill(self):
        '''Kill all processes and child processes'''

        try:
            log.info("Kill Tree parent pid: {0}".format(self.pid))
            parent = psutil.Process(self.pid)
            children = parent.children(recursive=True)
        except psutil.NoSuchProcess:
            log.info("Parent pid {0} is already dead".format(self.pid))
            # Already dead
            parent = None
            children = []
        if WIN:
            err = self.kill_job()
            msg = 'job'
        else:
            err = self.kill_pg()
            msg = 'process group'
        if parent and parent.is_running():
            log.info("BuildProcess.kill: parent pid {} is being killed".format(parent.pid))
            super(BuildProcess, self).kill()

        for child in children:
            if child.is_running():
                log.info("BuildProcess.kill: child pid {} is being killed".format(child.pid))
                child.kill()


