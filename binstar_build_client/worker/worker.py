"""
The worker 
"""
from __future__ import print_function, absolute_import, unicode_literals

from contextlib import contextmanager
import logging
import os
import time

from binstar_build_client.utils.rm import rm_rf
from binstar_client import errors
import psutil
import requests
import yaml

from .utils.buffered_io import BufferedPopen
from .utils.build_log import BuildLog
from .utils.script_generator import gen_build_script, \
    EXIT_CODE_OK, EXIT_CODE_ERROR, EXIT_CODE_FAILED
import inspect


log = logging.getLogger('binstar.build')

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

@contextmanager
def remove_files_after(files):
    try:
        yield
    finally:
        for filename in files:
            if os.path.isfile(filename):
                os.unlink(filename)



class Worker(object):
    """
    
    """
    STATE_FILE = 'worker.yaml'
    JOURNAL_FILE = 'journal.csv'
    SLEEP_TIME = 10

    def __init__(self, bs, args):
        self.bs = bs
        self.args = args

    def work_forever(self):
        """
        Start a loop and continuously build forever
        """
        log.info('Working Forever')
        with self.worker_context() as worker_id:
            self.worker_id = worker_id
            self._build_loop()

    def job_loop(self):
        """
        An iterator that will yield job_data objects when
        one is available. 
        
        Also handles journaling of jobs
        
        """
        bs = self.bs
        args = self.args
        worker_idle = False
        while 1:
            try:
                job_data = bs.pop_build_job(args.username, args.queue, self.worker_id)
            except errors.NotFound:

                if args.show_traceback:
                    raise
                else:
                    msg = ("This worker can no longer pop items off the build queue. "
                           "Did someone remove it manually?")
                    raise errors.BinstarError(msg)

            except requests.ConnectionError as err:
                log.error("Trouble connecting to binstar at '%s' " % bs.domain)
                log.error("Could not retrieve work items")
                job_data = {}
            except errors.ServerError as err:
                log.exception(err)
                log.error("There server '%s' returned an error response " % bs.domain)
                log.error("Could not retrieve work items")
                job_data = {}

            if job_data.get('job') is None:
                if not worker_idle:
                    idle_msg = 'Worker is waiting for the next job'
                    log.info(idle_msg)
                worker_idle = True
                time.sleep(self.SLEEP_TIME)
                continue

            worker_idle = False

            yield job_data

            if args.one:
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
        args = self.args

        if args.push_back:
            bs.push_build_job(args.username, args.queue, self.worker_id, job_data['job']['_id'])
        else:
            job_data = bs.fininsh_build(args.username, args.queue, self.worker_id, job_data['job']['_id'],
                                        failed=failed, status=status)

    def _build_loop(self):
        """
        This is the main build loop this checks binstar.org for any jobs it can do and 
        """

        with open(self.JOURNAL_FILE, 'a') as journal:
            for job_data in self.job_loop():
                with self.job_context(journal, job_data):
                    self._handle_job(job_data)


    def build(self, job_data):
        """
        Run a single build 
        """
        job_id = job_data['job']['_id']
        with BuildLog(self.bs, self.args.username, self.args.queue, self.worker_id, job_id) as build_log:


            instructions = job_data['build_item_info'].get('instructions')
            build_log.write("Building on worker %s (platform %s)\n" % (self.args.hostname, self.args.platform))
            build_log.write("Starting build %s\n" % job_data['job_name'])

            if not os.path.exists('build_scripts'):
                os.mkdir('build_scripts')

            script_filename = gen_build_script(job_data,
                                               conda_build_dir=self.args.conda_build_dir)

            iotimeout = instructions.get('iotimeout', 60)
            timeout = self.args.timeout

            api_token = job_data['upload_token']

            files = [script_filename]

            git_oauth_token = job_data.get('git_oauth_token')
            if not job_data.get('build_info', {}).get('github_info'):
                build_filename = self.download_build_source(job_id)
                files.append(build_filename)
            else:
                build_filename = None

            with remove_files_after(files):
                exit_code = self.run(job_data, script_filename, build_log,
                                     timeout, iotimeout,
                                     api_token, git_oauth_token, build_filename,
                                     instructions=instructions)

            log.info("Build script exited with code %s" % exit_code)
            if exit_code == EXIT_CODE_OK:
                failed = False
                status = 'success'
                log.info('Build %s Succeeded' % (job_data['job_name']))
            elif exit_code == EXIT_CODE_ERROR:
                failed = True
                status = 'error'
                log.error("Build %s errored" % (job_data['job_name']))
            elif exit_code == EXIT_CODE_FAILED:
                failed = True
                status = 'failure'
                log.error("Build %s failed" % (job_data['job_name']))
            else:  # Unknown error
                failed = True
                status = 'error'
                log.error("Unknown build exit status %s for build %s" % (exit_code, job_data['job_name']))

            return failed, status

    def run(self, build_data, script_filename, build_log, timeout, iotimeout,
            api_token=None, git_oauth_token=None, build_filename=None, instructions=None):


        owner = build_data['owner']['login']
        package = build_data['package']['name']

        working_dir = os.path.abspath(os.path.join('builds', owner, package))
        rm_rf(working_dir)
        os.makedirs(working_dir)

        args = [os.path.abspath(script_filename), '--api-token', api_token]


        if git_oauth_token:
            args.extend(['--git-oauth-token', git_oauth_token])

        elif build_filename:
            args.extend(['--build-tarball', build_filename])

        log.info("Running command: (iotimeout=%s)" % iotimeout)
        log.info(" ".join(args))

        if self.args.show_new_procs:
            already_running_procs = get_my_procs()

        p0 = BufferedPopen(args, stdout=build_log, iotimeout=iotimeout, cwd=working_dir)

        try:
            exit_code = p0.wait()
        except BaseException:
            log.error("Binstar build process caught an exception while waiting for the build to finish")
            p0.kill_tree()
            p0.wait()
            raise
        finally:
            if self.args.show_new_procs:
                currently_running_procs = get_my_procs()
                new_procs = [psutil.Process(pid) for pid in currently_running_procs - already_running_procs]
                if new_procs:
                    build_log.write("WARNING: There are processes that were started during the build and are still running\n")
                    for proc in new_procs:
                        build_log.write(" - Process name:%s pid:%s\n" % (proc.name, proc.pid))
                        try:
                            cmdline = ' '.join(proc.cmdline)
                        except:
                            pass
                        else:
                            build_log.write("    + %s\n" % cmdline)


        return exit_code

    def download_build_source(self, job_id):
        """
        If the source files for this job were tarred and uploaded to bisntar.
        Download them. 
        """
        log.info("Fetching build data")
        if not os.path.exists('build_data'):
            os.mkdir('build_data')

        build_filename = os.path.join('build_data', '%s.tar.bz2' % job_id)
        fp = self.bs.fetch_build_source(self.args.username, self.args.queue, self.worker_id, job_id)

        with open(build_filename, 'wb') as bp:
            data = fp.read(2 ** 13)
            while data:
                bp.write(data)
                data = fp.read(2 ** 13)

        log.info("Wrote build data to %s" % build_filename)
        return os.path.abspath(build_filename)


    @contextmanager
    def worker_context(self):
        '''
        Register the worker with binstar and clean up on any excpetion or exit
        '''
        os.chdir(self.args.cwd)

        if os.path.isfile(self.STATE_FILE):
            with open(self.STATE_FILE, 'r') as fd:
                worker_data = yaml.load(fd)

            self.bs.remove_worker(self.args.username, self.args.queue, worker_data['worker_id'])
            log.info("Un-registered worker %s from binstar site" % worker_data['worker_id'])
            os.unlink(self.STATE_FILE)
            log.info("Removed worker.yaml")

        worker_id = self.bs.register_worker(self.args.username, self.args.queue, self.args.platform,
                                            self.args.hostname, self.args.dist)
        worker_data = {'worker_id': worker_id}

        with open(self.STATE_FILE, 'w') as fd:
            yaml.dump(worker_data, fd)
        try:
            yield worker_id
        finally:
            log.info("Removing worker %s" % worker_id)
            try:
                self.bs.remove_worker(self.args.username, self.args.queue, worker_id)
                os.unlink(self.STATE_FILE)
            except Exception as err:
                log.exception(err)
            log.debug("Removed %s" % self.STATE_FILE)

    @contextmanager
    def job_context(self, journal, job_data):
        """
        Yields a context where a job can execute safely
        
        If the context is not exited within 'args.timeout' seconds, an exception will be raised
        """
        ctx = (job_data['job']['_id'], job_data['job_name'])

        log.info('Starting build, %s, %s' % ctx)
        journal.write('starting build, %s, %s\n' % ctx)

        start_time = time.time()
        log.info('Setting alarm to terminate build after %i seconds' % self.args.timeout)

        try:
            yield
        except Exception as err:
            journal.write('build errored, %s, %s\n' % ctx)
            log.exception(err)
            time.sleep(self.SLEEP_TIME)
        else:
            journal.write('finished build, %s, %s\n' % ctx)
        finally:
            duration = time.time() - start_time
            log.info('Build Duration %i seconds' % duration)

