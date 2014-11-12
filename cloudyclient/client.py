import os.path as op
import logging
import threading

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
import pkg_resources

from cloudyclient.conf import settings


logger = logging.getLogger(__name__)


class CloudyClient(object):
    '''
    Encapsulates communications with the cloudy-release server for a single
    deployment.

    The constructor takes a deployment's *poll_url*. If *dry_run* is True,
    status changes are not sent to the server.
    '''

    _sessions = threading.local()

    def __init__(self, poll_url, dry_run=False, register_node=True):
        self.poll_url = poll_url
        self.dry_run = dry_run
        self.register_node = register_node
        self.version = pkg_resources.require('cloudy-release-client')[0].version

    def _get_http_adapter(self):
        return HTTPAdapter(max_retries=settings.requests_retries,
                pool_maxsize=settings.requests_pool_size,
                pool_connections=settings.requests_pool_size)

    def _get_session(self):
        '''
        Get the thread-local :class:`requests.Session` object used for all
        requests.
        '''
        if not hasattr(self._sessions, 'session'):
            session = requests.Session()
            if settings.secret is not None:
                session.headers['Authorization'] = \
                        'Secret %s' % settings.secret
            session.mount('http://', self._get_http_adapter())
            session.mount('https://', self._get_http_adapter())
            self._sessions.session = session
        return self._sessions.session

    def _request(self, method, *args, **kwargs):
        kwargs['timeout'] = settings.requests_timeout
        session = self._get_session()
        func = getattr(session, method)
        resp = func(*args, **kwargs)
        try:
            resp.raise_for_status()
        except HTTPError as exc:
            if exc.response.status_code == 403:
                print 'Authentication failed, check you have the correct ' \
                        'secret in ~/.config/cloudy/client.yml and you ' \
                        'have access to this deployment'
                exc.printed = True
                exc.final = True
            raise
        return resp

    def get(self, *args, **kwargs):
        return self._request('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._request('post', *args, **kwargs)

    def poll(self):
        '''
        Poll deployment informations from the server.
        '''
        if self.register_node:
            params = {'node_name': settings.node_name}
        else:
            params = None
        resp = self.get(self.poll_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        data['base_dir'] = op.expanduser(data['base_dir'])
        self.update_status_url = data['update_status_url']
        self.source_url = data['source_url']
        self.commit_url = data['commit_url']
        self.deployment_name = '{project_name}/{deployment_name}'.format(**data)
        return data

    def pending(self):
        '''
        Set this node's status to pending.
        '''
        if self.dry_run:
            return
        resp = self.post(self.update_status_url, data={
            'node_name': settings.node_name,
            'status': 'pending',
            'source_url': self.source_url,
            'client_version': self.version,
        })
        resp.raise_for_status()

    def error(self, output):
        '''
        Set this node's status to error.
        '''
        if self.dry_run:
            return
        resp = self.post(self.update_status_url, data={
            'node_name': settings.node_name,
            'status': 'error',
            'source_url': self.source_url,
            'output': output,
            'client_version': self.version,
        })
        resp.raise_for_status()

    def success(self, output):
        '''
        Set this node's status to success.
        '''
        if self.dry_run:
            return
        resp = self.post(self.update_status_url, data={
            'node_name': settings.node_name,
            'status': 'success',
            'source_url': self.source_url,
            'output': output,
            'client_version': self.version,
        })
        resp.raise_for_status()

    def get_commit(self):
        '''
        Retrieve the current commit of a deployment.
        '''
        resp = self.get(self.commit_url)
        resp.raise_for_status()
        return resp.json()

    def set_commit(self, commit):
        '''
        Set the current commit of a deployment.
        '''
        resp = self.post(self.commit_url, data={'commit': commit})
        resp.raise_for_status()
