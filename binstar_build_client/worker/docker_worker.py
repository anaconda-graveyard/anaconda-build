from __future__ import print_function
import logging
import os
from os.path import basename, abspath

from binstar_build_client.worker.utils.streamio import IOStream
from binstar_build_client.worker.worker import Worker
from requests import ConnectionError
from binstar_client import errors
import json

log = logging.getLogger("binstar.build")

try:
    import docker
except ImportError:
    docker = None


class DockerWorker(Worker):
    """
    """
    def __init__(self, bs, args):
        Worker.__init__(self, bs, args)

        self.client = docker.Client(base_url=os.environ.get('DOCKER_HOST'))
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
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None):
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
        stream = cli.attach(cont, stream=True, stdout=True, stderr=True)

        def timeout_callback(reason='iotimeout'):

            cli.kill(cont)

            if reason == 'iotimeout':
                build_log.write("\nTimeout: No output from program for %s seconds\n" % iotimeout)
                build_log.write("\nTimeout: If you require a longer timeout you "
                          "may set the 'iotimeout' variable in your .binstar.yml file\n")
                self._output.write("[Terminating]\n")
            elif reason == 'timeout':
                build_log.write("\nTimeout: build exceeded maximum build time of %s seconds\n" % timeout)
                build_log.write("[Terminating]\n")
            else:
                build_log.write("\nTerminate: User requested build to be terminated\n")
                build_log.write("[Terminating]\n")


        ios = IOStream(stream, build_log, iotimeout, timeout, timeout_callback)

        build_log.write("Docker: Start\n")

        ios.start()

        log.info("Binds: %r" % binds)

        cli.start(cont, binds=binds)

        exit_code = cli.wait(cont)

        ios.join()

        log.info("Remove Container: %r" % cont)
        cli.remove_container(cont, v=True)

        return exit_code



