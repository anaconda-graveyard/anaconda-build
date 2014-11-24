'''
Created on Aug 1, 2013

@author: sean
'''

from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from binstar_client.utils import jencode, compute_hash
from binstar_client.requests_ext import stream_multipart
import requests
from binstar_client.errors import BinstarError

class BuildMixin(object):
    '''
    Add build functionality to binstar client
    '''

    def set_keyfile(self, username, package, filename, content):
        url = '%s/build/%s/%s/keyfile' % (self.domain, username, package)
        data, headers = jencode(filename=filename, content=content)
        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res, [201])
    def remove_keyfile(self, username, package, filename):
        url = '%s/build/%s/%s/keyfile' % (self.domain, username, package)
        params = dict(filename=filename)
        res = self.session.delete(url, params=params)
        self._check_response(res, [201])

    def keyfiles(self, username, package):
        url = '%s/build/%s/%s/keyfiles' % (self.domain, username, package)
        res = self.session.get(url)
        self._check_response(res)
        return res.json()

    def submit_for_build(self, username, package, fd, instructions,
                         test_only=False, channels=None, queue=None, queue_tags=None, callback=None):

        url = '%s/build/%s/%s/stage' % (self.domain, username, package)
        data, headers = jencode(instructions=instructions, test_only=test_only, channels=channels, queue_name=queue, queue_tags=queue_tags)

        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res)
        obj = res.json()

        s3url = obj['post_url']
        s3data = obj['form_data']

        _hexmd5, b64md5, size = compute_hash(fd)
        s3data['Content-Length'] = size
        s3data['Content-MD5'] = b64md5

        data_stream, headers = stream_multipart(s3data, files={'file':(obj['basename'], fd)},
                                                callback=callback)

        s3res = requests.post(s3url, data=data_stream, verify=True, timeout=10 * 60 * 60, headers=headers)

        if s3res.status_code != 201:
            raise BinstarError('Error uploading build', s3res.status_code)

        url = '%s/build/%s/%s/commit/%s' % (self.domain, username, package, obj['build_id'])
        res = self.session.post(url, verify=True)
        self._check_response(res, [201])
        return obj

    def submit_for_url_build(self, username, package, instructions,
                             test_only=False, callback=None,
                             channels=None, queue=None, queue_tags=None, sub_dir='',
                             filter_platform=None):

        # /build/<owner_login>/<package_name>/submit-git-url
        url = '%s/build/%s/%s/submit-git-url' % (self.domain, username, package)

        data, headers = jencode(instructions=instructions, test_only=test_only,
                                channels=channels, sub_dir=sub_dir,
                                queue_name=queue, queue_tags=queue_tags,
                                filter_platform=filter_platform)

        res = self.session.post(url, data=data, headers=headers)

        self._check_response(res, [201])
        obj = res.json()
        return obj

    def builds(self, username, package, build_no=None):
        if build_no:
            url = '%s/build/%s/%s/%s' % (self.domain, username, package, build_no)
        else:
            url = '%s/build/%s/%s' % (self.domain, username, package)
        res = self.session.get(url)
        self._check_response(res)
        return res.json()

    def stop_build(self, username, package, build_id):
        url = '%s/build/%s/%s/stop/%s' % (self.domain, username, package, build_id)
        res = self.session.post(url)
        self._check_response(res, [201])
        return

    def tail_build(self, username, package, build_id, limit='', after=''):
        url = '%s/build/%s/%s/tail/%s' % (self.domain, username, package, build_id)
        res = self.session.get(url, params={'limit':limit, 'after': after})
        self._check_response(res, [200])
        return res.json()

    def resubmit_build(self, username, package, build_id):
        url = '%s/build/%s/%s/resubmit/%s' % (self.domain, username, package, build_id)
        res = self.session.post(url)
        self._check_response(res, [201])
        return

    def add_ci(self, username, package,
                   ghowner, ghrepo,
                   channels, queue=None, sub_dir=None,
                   branch='master', email=None):

        url = '%s/build/%s/%s/ci' % (self.domain, username, package)
        data, headers = jencode(ghowner=ghowner, ghrepo=ghrepo,
                                channels=channels, queue_name=queue, sub_dir=sub_dir,
                                branch=branch,
                                email=email,
                                )
        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res, [201])

    def remove_ci(self, username, package):
        url = '%s/build/%s/%s/ci' % (self.domain, username, package)
        res = self.session.delete(url)
        self._check_response(res, [201])

    def trigger_build(self, username, package, channels=None,
                      queue_name=None, branch=None, test_only=False,
                      filter_platform=None):
        url = '%s/build/%s/%s/trigger' % (self.domain, username, package)

        data, headers = jencode(channels=channels, queue_name=queue_name,
                                branch=branch, test_only=test_only,
                                filter_platform=filter_platform)

        res = self.session.post(url, data=data, headers=headers)
        self._check_response(res, [201])

        obj = res.json()
        return obj['build_no']


    def upload_test_results(self, action, username, package, major, minor, fd):
        url = '%s/build/%s/%s/results/%i/%i/%s' % (self.domain, username, package, major, minor, action)
        headers = {'Content-Type': 'application/xml'}
        res = self.session.post(url, data=fd.read(), headers=headers)
        self._check_response(res)

        return

