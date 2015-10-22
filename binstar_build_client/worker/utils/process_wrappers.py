import logging
import psutil
import subprocess

log = logging.getLogger('binstar.build')


class DockerBuildProcess(object):
    def __init__(self, cli, cont):
        self.cli = cli
        self.cont = cont
        self.stream = self.cli.attach(cont, stream=True, stdout=True, stderr=True)

    def kill(self):
        self.cli.kill(self.cont)

    def wait(self):
        return self.cli.wait(self.cont)

    def remove(self):
        self.cli.remove_container(self.cont, v=True)

    def readline(self):
        return next(self.stream, '')


class BuildProcess(subprocess.Popen):

    def __init__(self, args, cwd):

        super(BuildProcess, self).__init__(args=args, cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def kill(self):
        '''Kill all processes and child processes'''
        try:
            log.warning("Kill Tree parent pid: {0}".format(self.pid))
            parent = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            log.warning("Parent pid {0} is already dead".format(self.pid))
            # Already dead
            return

        children = parent.children(recursive=True)

        self.kill()
        for child in children:
            if child.is_running():
                log.warning(" - Kill child pid {}".format(child.pid))
                child.kill()

    def readlines(self):
        return self.stdout.readline()
