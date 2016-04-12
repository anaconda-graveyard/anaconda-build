import logging

import requests

from binstar_client import errors
from binstar_client.utils import jencode
import binstar_client
import binstar_build_client
from binstar_build_client.utils.worker_stats import worker_stats

log = logging.getLogger('binstar.build')

class BuildQueueMixin(object):

    def register_worker(self, username, queue_name, platform, hostname, dist, name):
        url = '%s/build-worker/%s/%s' % (self.domain, username, queue_name)
        data, headers = jencode(platform=platform, hostname=hostname, dist=dist,
                                binstar_version=binstar_client.__version__,
                                binstar_build_version=binstar_build_client.__version__,
                                name=name)
        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res, [200])
        return res.json()['worker_id']

    def remove_worker(self, username, queue_name, worker_id):
        '''Un-register a worker

        returns true if worker existed and was removed
        '''

        url = '%s/build-worker/%s/%s/%s' % (self.domain, username, queue_name, worker_id)
        res = self.session.delete(url)
        self._check_response(res, [200, 404])
        return res.status_code == 200

    def pop_build_job(self, username, queue_name, worker_id):
        '''Un-register a worker

        returns true if worker existed and was removed
        '''

        url = '%s/build-worker/%s/%s/%s/jobs' % (self.domain, username, queue_name, worker_id)
        res = self.session.post(url)
        self._check_response(res, [200])
        return res.json()

    def log_build_output(self, username, queue_name, worker_id, job_id, msg):
        '''Fallback log handler if /tagged-log endpoint does not exist'''
        url = '%s/build-worker/%s/%s/%s/jobs/%s/log' % (self.domain, username, queue_name, worker_id, job_id)
        res = self.session.post(url, data=msg)
        self._check_response(res, [201, 200])

        try:
            result = res.json().get('terminate_build', False)
        except ValueError:
            result = False

        return result

    def log_build_output_structured(self,
                                    username,
                                    queue_name,
                                    worker_id,
                                    job_id,
                                    msg,
                                    metadata):
        '''Call /tagged-log endpoint or fallback to plain log '''
        if getattr(self, 'log_build_output_structured_failed', False):
            return self.log_build_output(username, queue_name, worker_id,
                                         job_id, msg)
        url = '%s/build-worker/%s/%s/%s/jobs/%s/tagged-log' % (self.domain, username, queue_name, worker_id, job_id)
        content = metadata.copy()
        content['msg'] = msg
        res = self.session.post(url, data=content)
        try:
            self._check_response(res, [201, 200])
        except errors.NotFound:
            if hasattr(self, 'log_build_output_structured_failed'):
                # it might be a missing build or job that's not found.
                # structured log has succeeded at least once, so don't give up!
                raise

            log.info('Will not attempt structured '
                     'logging with tags, falling back '
                     'to plain build log.  There is no '
                     'Repository endpoint %s', url, exc_info=True)
            self.log_build_output_structured_failed = True
            return self.log_build_output(username, queue_name,
                                  worker_id, job_id,
                                  msg)
        else:
            self.log_build_output_structured_failed = False

        try:
            result = res.json().get('terminate_build', False)
        except ValueError:
            result = False

        return result

    def finish_build(self, username, queue_name, worker_id, job_id, status='success', failed=False):
        url = '%s/build-worker/%s/%s/%s/jobs/%s/finish' % (self.domain, username, queue_name, worker_id, job_id)
        data, headers = jencode(status=status, failed=failed)
        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res, [200])
        return res.json()

    def push_build_job(self, username, queue_name, worker_id, job_id):
        url = '%s/build-worker/%s/%s/%s/jobs/%s/push' % (self.domain, username, queue_name, worker_id, job_id)
        res = self.session.post(url)
        self._check_response(res, [201])
        return

    def fetch_build_source(self, username, queue_name, worker_id, job_id):
        url = '%s/build-worker/%s/%s/%s/jobs/%s/build-source' % (self.domain, username, queue_name, worker_id, job_id)

        res = self.session.get(url, allow_redirects=False, stream=True)

        self._check_response(res, allowed=[302, 304, 200])

        if res.status_code == 304:
            return None
        elif res.status_code == 302:
            res = requests.get(res.headers['location'], stream=True, verify=True)

        return res.raw

    def build_queues(self, username=None):
        if username:
            url = '%s/build-queues/%s' % (self.domain, username)
        else:
            url = '%s/build-queues' % (self.domain)

        res = self.session.get(url)
        self._check_response(res)
        return res.json()

    def build_queue(self, username, queuename):
        url = '%s/build-queues/%s/%s' % (self.domain, username, queuename)

        res = self.session.get(url)
        self._check_response(res)
        return res.json()


    def remove_build_queue(self, username, queuename):

        url = '%s/build-queues/%s/%s' % (self.domain, username, queuename)
        res = self.session.delete(url)
        self._check_response(res, [201])
        return

    def add_build_queue(self, username, queuename):

        url = '%s/build-queues/%s/%s' % (self.domain, username, queuename)

        data, headers = jencode()
        res = self.session.post(url, data=data, headers=headers)

        self._check_response(res, [201])
        return

    def build_backlog(self, username, queuename):
        url = '%s/build-queues/%s/%s/jobs' % (self.domain, username, queuename)
        res = self.session.get(url)

        self._check_response(res, [200])
        return res.json().get('jobs', [])

    def upload_worker_stats(self, username, queue_name, worker_id):
        url = '%s/build-worker/%s/%s/%s/worker-stats' % (self.domain, username, queue_name, worker_id)
        data, headers = jencode(worker_stats=worker_stats())
        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res, [201])
        return res.json()
