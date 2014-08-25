import sys

class BuildLog(object):
    def __init__(self, bs, username, queue, worker_id, job_id):
        self.bs = bs
        self.username = username
        self.queue = queue
        self.worker_id = worker_id
        self.job_id = job_id

    def write(self, msg):
        self.bs.log_build_output(self.username, self.queue, self.worker_id, self.job_id, msg)
        n = sys.stdout.write(msg)
        return n
