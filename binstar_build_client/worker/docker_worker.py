from __future__ import print_function, unicode_literals, absolute_import

import json
import logging
import os
from os.path import basename, abspath

from binstar_build_client.worker.utils.build_log import BuildLog
from binstar_build_client.worker.worker import Worker
from binstar_client import errors

from requests import ConnectionError


log = logging.getLogger("binstar.build")

try:
    import docker
    from docker.utils import kwargs_from_env
except ImportError:
    docker = None

class DockerBuildProcess(object):
    def __init__(cli, cont):
        self.cli = cli
        self.cont = cont
        self.stream = self.cli.attach(cont, stream=True, stdout=True, stderr=True)

    def kill(self):
        self.cli.kill(self.cont)
        self.cli.remove_container(self.cont, v=True)

    def readline(self):
        return self.stream.next()

class DockerWorker(Worker):
    """
    """
    def __init__(self, bs, worker_config, args):
        Worker.__init__(self, bs, worker_config, args)

        self.client = docker.Client(**kwargs_from_env(assert_hostname=False))
        log.info('Connecting to docker daemon ...')
        try:
            images = self.client.images(args.image)
        except ConnectionError as err:
            raise errors.BinstarError("Docker client could not connect to daemon (is docker installed?)\n"
                                      "You may need to set your DOCKER_HOST environment variable")
        if not images:
            raise errors.BinstarError("You do not have the docker image '%(image)s'\n"
                                      "You may need to run:\n\n\tdocker pull %(image)s\n" % dict(image=args.image))

        if self.args.allow_user_images:
            log.warn("Allowing users to specify docker images")


    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None,
            build_was_stopped_by_user=lambda:None):
        """
        """
        cli = self.client
        image = self.args.image
        container_script_filename = '/%s' % basename(script_filename)

        volumes = [container_script_filename,
                   ]
        binds = {abspath(script_filename): {'bind': container_script_filename, 'ro': False}}

        args = ["bash", container_script_filename, '--api-token', api_token]

        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            container_build_filename = '/%s' % basename(build_filename)
            volumes.append(container_build_filename)
            binds[build_filename] = {'bind': container_build_filename, 'ro': False}
            args.extend(['--build-tarball', container_build_filename])

        log.info("Running command: (iotimeout=%s)" % iotimeout)
        if self.args.allow_user_images:
            if instructions and instructions.get('docker_image'):
                image = instructions['docker_image']
                if ':' in image:
                    repository, tag = image.rsplit(':', 1)
                else:
                    repository, tag = image, None

                build_log.write('Docker: Pull %s\n' % image)
                for line in cli.pull(repository, tag=tag, stream=True):
                    msg = json.loads(line)
                    if msg.get('status') == 'Downloading':
                        build_log.write('.')
                    elif msg.get('status'):
                        build_log.write(msg.get('status', '') + '\n')
                    else:
                        build_log.write(line + '\n')

        else:
            if instructions and instructions.get('docker_image'):
                build_log.write("WARNING: User specified images are not allowed on this build worker\n")
                build_log.write("Using default docker image\n")

        command = " ".join(args)
        log.info(command)
        build_log.write("Docker Image: %s\n" % image)
        log.info("Volumes: %r" % volumes)

        build_log.write("Docker: Create container\n")
        cont = cli.create_container(image, command=command, volumes=volumes)

        build_log.write("Docker: Attach output\n")

        # def timeout_callback(reason='iotimeout'):

        #     log.info("timeout occurred: {}".format(reason))
        #     log.info("killing docker container")

        #     cli.kill(cont)
        #     if reason == 'iotimeout':
        #         build_log.write("\nTimeout: No output from program for %s seconds\n" % iotimeout)
        #         build_log.write("\nTimeout: If you require a longer timeout you "
        #                   "may set the 'iotimeout' variable in your .binstar.yml file\n")
        #         build_log.write("[Terminating]\n")
        #     elif reason == 'timeout':
        #         build_log.write("\nTimeout: build exceeded maximum build time of %s seconds\n" % timeout)
        #         build_log.write("[Terminating]\n")
        #     else:
        #         build_log.write("\nTerminate: User requested build to be terminated\n")
        #         build_log.write("[Terminating]\n")

        build_log.write("Docker: Start\n")
        p0 = DockerBuildProcess(cli, cont)
        log.info("Binds: %r" % binds)

        cli.start(cont, binds=binds)

        # ios = IOStream(stream, build_log, iotimeout, timeout, timeout_callback)
        try:
            read_with_timeout(p0, build_log, timeout, iotimeout, BuildLog.INTERVAL,
                             build_was_stopped_by_user)
        except BaseException:
            log.error("Binstar build process caught an exception while waiting for the build to finish")
            p0.kill()
            p0.wait()
            raise

        exit_code = cli.wait(cont)

        log.info("Remove Container: %r" % cont)
        cli.remove_container(cont, v=True)

        return exit_code



