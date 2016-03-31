"""
The worker
"""
from __future__ import print_function, absolute_import, unicode_literals

from contextlib import contextmanager
import datetime
import inspect
import io
import logging
import os
import psutil
import requests
import time


from binstar_build_client.utils.rm import rm_rf
from binstar_build_client.worker.utils import process_wrappers
from binstar_build_client.worker.utils import script_generator
from binstar_build_client.worker.utils.build_log import BuildLog
from binstar_build_client.worker.utils.timeout import read_with_timeout
from binstar_client import errors


log = logging.getLogger('binstar.build')

DEFAULT_IO_TIMEOUT = 60 * 5

def get_my_procs():
    this_proc = psutil.Process()
    if os.name == 'nt':
        myusername = this_proc.username()
        def ismyproc(proc):
            try:
                return proc.username() == myusername
            except psutil.AccessDenied:
                return False
    else:
        def ismyproc(proc):
            if inspect.isroutine(this_proc.uids):
                # psutil >= 2
                return proc.uids().real == this_proc.uids().real
            else:
                # psutil < 2
                return proc.uids.real == this_proc.uids.real
    return {proc.pid for proc in psutil.process_iter() if ismyproc(proc)}


class Worker(object):
    """

    """
    JOURNAL_FILE = 'journal.csv'
    SLEEP_TIME = 10

    def __init__(self, bs, worker_config, args):
        self.bs = bs
        self.args = args
        self.config = worker_config

    @property
    def worker_id(self):
        return self.config.worker_id

    def write_status(self, ok=True, msg='ok'):
        if self.args.status_file:
            with open(self.args.status_file, 'w') as fd:
                fd.write("{0} {1} '{2}'\n".format(int(not ok), int(time.time()), msg))

    def write_stats(self):
        try:
            self.bs.upload_worker_stats(self.config.username,
                                        self.config.queue,
                                        self.worker_id)
        except errors.NotFound:
            log.warn('{} does not support upload '
                     'of worker status information like system '
                     'packages and the output of conda list.'
                     '  It may be an out of date '
                     'version of Repository'.format(self.bs.domain))

    def job_loop(self):
        """
        An iterator that will yield job_data objects when
        one is available.

        Also handles journaling of jobs

        """
        bs = self.bs
        worker_idle = False
        while 1:
            try:
                job_data = bs.pop_build_job(self.config.username,
                                            self.config.queue,
                                            self.worker_id)

            except errors.NotFound:
                self.write_status(False, "worker not found")
                if self.args.show_traceback:
                    raise
                else:
                    msg = ("This worker can no longer "
                           "pop items off the build queue. "
                           "Did someone remove it manually?")
                    raise errors.BinstarError(msg)

            except requests.ConnectionError as err:
                log.error("Trouble connecting to binstar at '{0}' ".format(bs.domain))
                log.error("Could not retrieve work items")
                job_data = {}
                self.write_status(False, "Trouble connecting to binstar")

            except errors.ServerError as err:
                log.exception(err)
                log.error("There server '{0}' returned an error response ".format(bs.domain))
                log.error("Could not retrieve work items")
                self.write_status(False, "Server error")
                job_data = {}
            else:
                self.write_status(True)

            if job_data.get('job') is None:
                if not worker_idle:
                    idle_msg = 'Worker is waiting for the next job'
                    log.info(idle_msg)
                worker_idle = True
                time.sleep(self.SLEEP_TIME)
                continue

            worker_idle = False

            yield job_data

            if self.args.one:
                break


    def _handle_job(self, job_data):
        """
        Handle a single build job
        only catches build script level errors
        """

        try:
            failed, status = self.build(job_data)
        except Exception as err:
            # Catch all exceptions here and submit a build error
            log.exception(err)
            failed = True
            status = 'error'
        except BaseException as err:
            # Catch all exceptions here and submit a build error
            log.exception(err)
            failed = True
            status = 'error'
            self._finish_job(job_data, failed, status)
            raise

        self._finish_job(job_data, failed, status)


    def _finish_job(self, job_data, failed, status):
        bs = self.bs

        if self.args.push_back:
            bs.push_build_job(
                self.config.username,
                self.config.queue,
                self.worker_id,
                job_data['job']['_id']
            )
        else:
            job_data = bs.finish_build(
                self.config.username,
                self.config.queue,
                self.worker_id,
                job_data['job']['_id'],
                failed=failed,
                status=status
            )

    def work_forever(self):
        """
        Start a loop and continuously build forever
        This is the main build loop this checks anaconda.org for any jobs it can do and
        """
        log.info('Working Forever')

        with open(self.JOURNAL_FILE, 'a') as journal:
            for job_data in self.job_loop():
                with self.job_context(journal, job_data):
                    self._handle_job(job_data)

    def working_dir(self, job_data):
        '''The location where the build process should `cd`
        before execution. Relative to the container file system.

        :param job_data: the job information
        :return: path (str)
        '''
        return self.staging_dir(job_data)

    def staging_dir(self, job_data):
        '''
        The location where the build files for this job should be created
        while setting up

        :param job_data: The job information
        :return:  path (str)
        '''

        owner = job_data['owner']['login']
        package = job_data['package']['name']

        working_dir = os.path.join(self.args.cwd, 'builds', owner, package)
        working_dir = os.path.abspath(working_dir)

        return working_dir

    def build_logfile(self, build_data):

        staging_dir = self.staging_dir(build_data)
        filename = os.path.abspath(os.path.join(staging_dir, 'build-log.txt'))

        log.info("Writing build log to file {0}".format(filename))
        return filename

    def build(self, job_data):
        """
        Run a single build
        """
        job_id = job_data['job']['_id']
        if 'envvars' in job_data['build_item_info']:
            job_data['build_item_info']['env'] = job_data['build_item_info'].pop('envvars')

        working_dir = self.working_dir(job_data)
        staging_dir = self.staging_dir(job_data)

        # -- Clean --
        log.info("Removing previous build dir: {0}".format(staging_dir))
        rm_rf(staging_dir)
        log.info("Creating working dir: {0}".format(staging_dir))
        os.makedirs(staging_dir)

        quiet = job_data['build_item_info'].get('instructions',{}).get('quiet', False)
        build_log = BuildLog(
            self.bs,
            self.config.username,
            self.config.queue,
            self.worker_id,
            job_id,
            filename=self.build_logfile(job_data),
            quiet=quiet,
        )

        build_log.update_metadata({'section': 'dequeue_build'})
        with build_log:
            instructions = job_data['build_item_info'].get('instructions')

            msg = "Building on worker {0} (platform {1})\n".format(
                    self.config.hostname, self.config.platform)
            build_log.writeline(msg.encode('utf-8', errors='replace'))
            msg = "Starting build {0} at {1}\n".format(job_data['job_name'], job_data['BUILD_UTC_DATETIME'])
            build_log.writeline(msg.encode('utf-8', errors='replace'))

            # build_log.flush()

            script_filename = script_generator.gen_build_script(
                staging_dir,
                working_dir,
                job_data,
                conda_build_dir=self.args.conda_build_dir)

            iotimeout = instructions.get('iotimeout', DEFAULT_IO_TIMEOUT)
            timeout = self.args.timeout

            api_token = job_data['upload_token']

            git_oauth_token = job_data.get('git_oauth_token')
            if not job_data.get('build_info', {}).get('github_info'):
                build_filename = self.download_build_source(staging_dir, job_id)
            else:
                build_filename = None

            exit_code = self.run(
                job_data, script_filename, build_log, timeout, iotimeout, api_token,
                git_oauth_token, build_filename, instructions=instructions,
                build_was_stopped_by_user=build_log.terminated)
            log.info("Build script exited with code {0}".format(exit_code))
            if exit_code == script_generator.EXIT_CODE_OK:
                failed = False
                status = 'success'
                log.info('Build {0} Succeeded'.format(job_data['job_name']))
            elif exit_code == script_generator.EXIT_CODE_ERROR:
                failed = True
                status = 'error'
                log.error("Build {0} errored".format(job_data['job_name']))
            elif exit_code == script_generator.EXIT_CODE_FAILED:
                failed = True
                status = 'failure'
                log.error("Build {0} failed".format(job_data['job_name']))
            else:  # Unknown error
                failed = True
                status = 'error'
                log.error("Unknown build exit status {0} for build {1}".format(
                    exit_code, job_data['job_name']))
            return failed, status

    def run(self, build_data, script_filename, build_log, timeout, iotimeout, api_token=None,
            git_oauth_token=None, build_filename=None, instructions=None,
            build_was_stopped_by_user=lambda:None):

        log.info("Running build script")

        working_dir = self.working_dir(build_data)

        args = [os.path.abspath(script_filename), '--api-token', api_token]

        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            args.extend(['--build-tarball', build_filename])

        log.info("Running command: (iotimeout={0})".format(iotimeout))
        log.info(" ".join(args))

        if self.args.show_new_procs:
            already_running_procs = get_my_procs()

        p0 = process_wrappers.BuildProcess(
            args,
            cwd=working_dir
        )

        log.info("Started build script with pid: {}".format(p0.pid))

        try:
            read_with_timeout(
                p0,
                build_log,
                timeout,
                iotimeout,
                BuildLog.INTERVAL,
                build_was_stopped_by_user,
            )
        except BaseException:
            log.error(
                "Anaconda build process caught an exception while waiting for the build to finish")
            p0.kill()
            p0.wait()
            raise
        finally:
            if self.args.show_new_procs:
                currently_running_procs = get_my_procs()
                new_procs = [
                    psutil.Process(pid) for pid in currently_running_procs - already_running_procs]
                if new_procs:
                    build_log.write(
                        "WARNING: There are processes that were started during the build and are"
                        "still running\n")
                    for proc in new_procs:
                        build_log.write(" - Process name: {0} pid:{1}\n".format(
                            proc.name, proc.pid))
                        try:
                            cmdline = ' '.join(proc.cmdline)
                        except:
                            pass
                        else:
                            build_log.write("    + {0}\n".format(cmdline))

        return p0.poll()

    def download_build_source(self, working_dir, job_id):
        """
        If the source files for this job were tarred and uploaded to bisntar.
        Download them.
        """
        log.info("Fetching build data")
        build_filename = os.path.join(working_dir, 'source.tar.bz2')

        fp = self.bs.fetch_build_source(
            self.config.username,
            self.config.queue,
            self.worker_id,
            job_id
        )

        with open(build_filename, 'wb') as bp:
            data = fp.read(2 ** 13)
            while data:
                bp.write(data)
                data = fp.read(2 ** 13)

        log.info("Wrote build data to {0}".format(build_filename))
        return os.path.abspath(build_filename)

    @contextmanager
    def job_context(self, journal, job_data):
        """
        Yields a context where a job can execute safely

        If the context is not exited within 'args.timeout' seconds, an exception will be raised
        """
        job_data['BUILD_UTC_DATETIME'] = datetime.datetime.utcnow().isoformat()
        ctx = (job_data['job']['_id'], job_data['job_name'], job_data['BUILD_UTC_DATETIME'])
        log.info('Starting build, {0}, {1} at {2}'.format(*ctx))
        journal.write('starting build, {0}, {1} at {2}\n'.format(*ctx))

        start_time = time.time()
        log.info('Setting alarm to terminate build after {0} seconds'.format(self.args.timeout))

        try:
            yield
        except Exception as err:
            journal.write('build errored, {0}, {1}\n'.format(*ctx))
            log.exception(err)
            time.sleep(self.SLEEP_TIME)
        else:
            journal.write('finished build, {0}, {1}\n'.format(*ctx))
        finally:
            duration = time.time() - start_time
            log.info('Build Duration {0} seconds'.format(duration))

