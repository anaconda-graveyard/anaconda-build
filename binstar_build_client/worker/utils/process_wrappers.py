import logging
import pipes
import psutil
import subprocess

from binstar_client.utils import get_config

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
        return next(self.stream, b'')


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

        super(BuildProcess, self).kill()
        for child in children:
            if child.is_running():
                log.warning(" - Kill child pid {}".format(child.pid))
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
        super(SuBuildProcess, self).__init__(args, cwd)

    def su_with_env(self, cmd):
        '''args for su as build_user with the anaconda settings'''
        cmds = ['su', '--login', '-c', self.source_env]
        cmds[-1] += " && anaconda config --set url {} && ".format(self.anaconda_url)
        cmds[-1] += " conda config --set always_yes true && "
        cmds[-1] += cmd
        cmds += ['-', self.build_user]
        return cmds

    @property
    def anaconda_url(self):
        config = get_config(remote_site=self.site)
        return config.get('url', 'https://api.anaconda.org')

    @property
    def source_env(self):
        return ("export PATH={0}/bin:${{PATH}} "
                "&& source activate anaconda.org ").format(self.python_install_dir)


