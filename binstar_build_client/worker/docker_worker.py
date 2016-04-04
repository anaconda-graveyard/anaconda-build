from __future__ import print_function, unicode_literals, absolute_import

import json
import logging
import os
import tarfile
from io import BytesIO
from os.path import basename

from binstar_client import errors
from requests import ConnectionError

from binstar_build_client.worker.utils.build_log import BuildLog
from binstar_build_client.worker.utils.process_wrappers import DockerBuildProcess
from binstar_build_client.worker.utils.timeout import read_with_timeout
from binstar_build_client.worker.worker import Worker


log = logging.getLogger("binstar.build")

try:
    import docker
    from docker.utils import kwargs_from_env
except ImportError:
    docker = None
    kwargs_from_env = None

class DockerWorker(Worker):
    """
    """
    def __init__(self, bs, worker_config, args):
        Worker.__init__(self, bs, worker_config, args)

        self.client = docker.Client(
            version=os.environ.get('DOCKER_VERSION'),
            **kwargs_from_env(assert_hostname=False)
        )
        log.info('Connecting to docker daemon ...')
        try:
            image = args.image
            if ':' in image:
                self.image, self.tag = image.split(':', 1)
            else:
                self.image, self.tag = image, None
            images = self.client.images(self.image)
        except ConnectionError as err:
            raise errors.BinstarError(
                "Docker client could not connect to daemon (is docker installed?)\n"
                "You may need to set your DOCKER_HOST environment variable")
        if not images:
            raise errors.BinstarError(
                "You do not have the docker image '{image}'\n"
                "You may need to run:\n\n\tdocker pull {image}s\n".format(image=args.image))

        if self.args.allow_user_images:
            log.warn("Allowing users to specify docker images")

    def working_dir(self, build_data):
        if not self.tag:
            find_match = self.image # no tag
            image = [img for img in self.client.images()
                     if find_match in {i.split(':', 1)[0] for i in img['RepoTags']}][0]
        else:
            find_match = self.args.image # with the tag
            image = [img for img in self.client.images()
                     if find_match in img['RepoTags']][0]

        return self.client.inspect_image(image)['Config']['WorkingDir']

    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None,
            build_was_stopped_by_user=lambda:None):
        """
        """
        cli = self.client
        image = self.args.image

        script_basename = basename(script_filename)
        # files to transfer into the working directory of the image
        transfer_files = [(script_filename, script_basename)]

        # TODO: working_dir should probably be extracted from the docker image definition (WORKDIR)
        working_dir = self.working_dir(build_data)
        container_script_filename = '{0}/{1}'.format(working_dir, script_basename)

        args = ["bash", container_script_filename, '--api-token', api_token]

        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            build_basename = basename(build_filename)
            container_build_filename = '{0}/{1}'.format(working_dir, build_basename)
            args.extend(['--build-tarball', container_build_filename])
            transfer_files.append((build_filename, build_basename))

        log.info("Running command: (iotimeout={0})".format(iotimeout))
        if self.args.allow_user_images:
            if instructions and instructions.get('docker_image'):
                image = instructions['docker_image']
                if ':' in image:
                    repository, tag = image.rsplit(':', 1)
                else:
                    repository, tag = image, None

                build_log.writeline(b'Docker: Pull {0}\n'.format(image))
                for index, line in enumerate(cli.pull(repository, tag=tag, stream=True)):
                    msg = json.loads(line)
                    if msg.get('status') == 'Downloading':
                        build_log.writeline(b'.' * index + '\r')
                    elif msg.get('status'):
                        build_log.writeline(msg.get('status', '').encode('utf-8', 'replace') + b'\n')
                    else:
                        build_log.writeline(line.encode('utf-8', 'replace') + b'\n')

        else:
            if instructions and instructions.get('docker_image'):
                build_log.writeline(b"WARNING: User specified images are not allowed on this build worker\n")
                build_log.writeline(b"Using default docker image\n")

        command = " ".join(args)
        log.info("Executing '%s' on docker", command)

        build_log.writeline("Docker Image: {0}\n".format(image).encode('utf8'))

        build_log.writeline(b"Docker: Create container\n")
        cont = cli.create_container(image, command=command)

        build_log.writeline(b"Docker: Attach output\n")

        archive = BytesIO()
        with tarfile.open(fileobj=archive, mode='w') as tf:
            for filename, arcname in transfer_files:
                tf.add(filename, arcname)
        archive.seek(0)

        put_success = cli.put_archive(cont, working_dir, archive)
        # build_log.write(b"Docker: Inserted script: %s\n" % put_success)

        build_log.writeline(b"Docker: Start\n")
        p0 = DockerBuildProcess(cli, cont)

        cli.start(cont)

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
            log.error("Binstar build process caught an exception while waiting for the build to finish")
            p0.kill()
            p0.wait()
            p0.remove()
            raise

        exit_code = p0.wait()

        log.info("Remove Container: {0}".format(cont))
        cli.remove_container(cont, v=True)

        return exit_code



