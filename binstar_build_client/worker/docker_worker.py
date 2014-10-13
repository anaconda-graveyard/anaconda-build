from __future__ import print_function
import logging
import os
from os.path import basename, abspath

from binstar_build_client.worker.utils.streamio import IOStream
from binstar_build_client.worker.worker import Worker
from requests import ConnectionError
from binstar_client import errors

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

        try:
            images = self.client.images(args.image)
        except ConnectionError as err:
            raise errors.BinstarError("Docker client could not connect to daemon (is docker installed?)\n"
                                      "You may need to set your DOCKER_HOST environment variable")
        if not images:
            raise errors.BinstarError("You do not have the docker image '%(image)s'\n"
                                      "You may need to run:\n\n\tdocker pull %(image)s\n" % dict(image=args.image))



    def run(self, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None):
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

        command = " ".join(args)
        log.info(command)
        log.info("Image: %s" % image)
        log.info("Volumes: %r" % volumes)

        cont = cli.create_container(image, command=command, volumes=volumes)

        stream = cli.attach(cont, stream=True, stdout=True, stderr=True)

        def timeout_callback(iotimeout=False):

            cli.kill(cont)

            if iotimeout:
                build_log.write("\nTimeout: No output from program for %s seconds\n" % iotimeout)
                build_log.write("\nTimeout: If you require a longer timeout you "
                          "may set the 'iotimeout' variable in your .binstar.yml file\n")
                self._output.write("[Terminating]\n")
            else:
                build_log.write("\nTimeout: build exceeded maximum build time of %s seconds\n" % timeout)
                build_log.write("[Terminating]\n")

        ios = IOStream(stream, build_log, iotimeout, timeout, timeout_callback)
        ios.start()

        log.info("Binds: %r" % binds)

        cli.start(cont, binds=binds)

        exit_code = cli.wait(cont)

        ios.join()

        return exit_code



