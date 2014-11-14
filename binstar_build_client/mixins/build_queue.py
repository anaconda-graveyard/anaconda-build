from binstar_client.utils import jencode
import requests
import binstar_client
import binstar_build_client

class BuildQueueMixin(object):

    def register_worker(self, username, queue_name, platform, hostname, dist):
        url = '%s/build-worker/%s/%s' % (self.domain, username, queue_name)
        data, headers = jencode(platform=platform, hostname=hostname, dist=dist,
                                binstar_version=binstar_client.__version__,
                                binstar_build_version=binstar_build_client.__version__)
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
        url = '%s/build-worker/%s/%s/%s/jobs/%s/log' % (self.domain, username, queue_name, worker_id, job_id)
        res = self.session.post(url, data=msg)
        self._check_response(res, [201, 200])

        try:
            result = res.json().get('terminate_build', False)
        except ValueError:
            result = False

        return result

    def fininsh_build(self, username, queue_name, worker_id, job_id, status='success', failed=False):
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

