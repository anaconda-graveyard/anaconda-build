"""
The worker 
"""
from contextlib import contextmanager
import logging
import os
from subprocess import Popen, PIPE
from subprocess import STDOUT
import time
import traceback

from binstar_build_client.worker.build_log import BuildLog
from binstar_build_client.worker.utils.buffered_io import BufferedPopen
from binstar_build_client.worker.utils.script_generator import gen_build_script
from binstar_client import errors
import yaml
import sys


log = logging.getLogger('binstar.build')

class IO(object):
    def write(self, data):
        print "IO", data,
        sys.stdout.flush()

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

    def job_loop(self, journal):
        bs = self.bs
        args = self.args
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

            if job_data.get('job') is None:
                time.sleep(self.SLEEP_TIME)
                continue

            ctx = (job_data['job']['_id'], job_data['job_name'])
            log.info('Starting build, %s, %s\n' % ctx)
            journal.write('starting build, %s, %s\n' % ctx)

            try:
                yield job_data
            except Exception:
                journal.write('build errored, %s, %s\n' % ctx)
                traceback.print_exc()
                time.sleep(self.SLEEP_TIME)
            else:
                journal.write('finished build, %s, %s\n' % ctx)

            if args.one:
                break



    def _handle_job(self, job_data):
        """
        Handle a single build job
        only catches build script level errors
        """
        bs = self.bs
        args = self.args

        try:
            failed, status = self.build(job_data)
        except Exception as err:
            log.exception(err)
            failed = True
            status = 'error'

        if args.push_back:
            bs.push_build_job(args.username, args.queue, self.worker_id, job_data['job']['_id'])
            raise
        else:
            job_data = bs.fininsh_build(args.username, args.queue, self.worker_id, job_data['job']['_id'],
                                        failed=failed, status=status)


    def _build_loop(self):
        """
        This is the main build loop this checks binstar.org for any jobs it can do and 
        """

        with open(self.JOURNAL_FILE, 'a') as journal:
            for job_data in self.job_loop(journal):
                self._handle_job(job_data)


    def build(self, job_data):
        """
        Run a single build 
        """
        job_id = job_data['job']['_id']
        build_log = BuildLog(self.bs, self.args.username, self.args.queue, self.worker_id, job_id)

        build_log.write("Building on worker %s (platform %s)\n" % (self.args.hostname, self.args.platform))
        build_log.write("Starting build %s\n" % job_data['job_name'])

        if not os.path.exists('build_scripts'):
            os.mkdir('build_scripts')

        script_filename = gen_build_script(job_data)


        iotimeout = job_data['build_item_info'].get('instructions').get('iotimeout', 60)
        args = [script_filename, '--api-token', job_data['upload_token']]

        if job_data.get('git_oauth_token'):
            args.extend(['--git-oauth-token', job_data.get('git_oauth_token')])
        else:
            build_filename = self.download_build_source(job_id)
            args.extend(['--build-tarball', build_filename])

        log.info("Running command: (iotimeout=%s)" % iotimeout)
        log.info(" ".join(args))

        p0 = BufferedPopen(args, stdout=build_log, iotimeout=iotimeout)
        exit_code = p0.wait()

        log.info("Build script exited with code %s" % exit_code)
        if exit_code == 0:
            failed = False
            status = 'success'
            log.info('Build %s Succeeded' % (job_data['job_name']))
        elif exit_code == 11:
            failed = True
            status = 'error'
            log.error("Build %s errored" % (job_data['job_name']))
        elif exit_code == 12:
            failed = True
            status = 'failure'
            log.error("Build %s failed" % (job_data['job_name']))
        else:  # Unknown error
            failed = True
            status = 'error'
            log.error("Unknown build exit status %s for build %s" % (exit_code, job_data['job_name']))

        aasdf

        return failed, status

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
            if self.args.clean:
                self.bs.remove_worker(self.args.username, self.args.queue, worker_data['worker_id'])
                log.info("Un-registered worker %s from binstar site" % worker_data['worker_id'])
                os.unlink(self.STATE_FILE)
                log.info("Removed worker.yaml")
                raise SystemExit()
            else:
                raise errors.UserError("Lock file '%s' exists. Use -c/--clean to remove this working context" % self.STATE_FILE)

        worker_id = self.bs.register_worker(self.args.username, self.args.queue, self.args.platform, self.args.hostname)
        worker_data = {'worker_id': worker_id}

        with open(self.STATE_FILE, 'w') as fd:
            yaml.dump(worker_data, fd)
        try:
            yield worker_id
        finally:
            log.info("Removing worker %s" % worker_id)
            self.bs.remove_worker(self.args.username, self.args.queue, worker_id)
            os.unlink(self.STATE_FILE)
            log.debug("Removed %s" % self.STATE_FILE)

