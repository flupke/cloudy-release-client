import os.path as op
import logging

import requests
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

    def __init__(self, poll_url, dry_run=False):
        self.poll_url = poll_url
        self.dry_run = dry_run
        self.version = pkg_resources.require('cloudy-release-client')[0].version

    def poll(self):
        '''
        Poll deployment informations from the server.
        '''
        resp = requests.get(self.poll_url, 
                params={'node_name': settings.NODE_NAME})
        resp.raise_for_status()
        data = resp.json()
        data['base_dir'] = op.expanduser(data['base_dir'])
        self.update_status_url = data['update_status_url']
        self.source_url = data['source_url']
        return data

    def pending(self):
        if self.dry_run:
            return
        resp = requests.post(self.update_status_url, data={
            'node_name': settings.NODE_NAME,
            'status': 'pending',
            'source_url': self.source_url,
            'client_version': self.version,
        })
        resp.raise_for_status()

    def error(self, output):
        if self.dry_run:
            return
        resp = requests.post(self.update_status_url, data={
            'node_name': settings.NODE_NAME,
            'status': 'error',
            'source_url': self.source_url,
            'output': output,
            'client_version': self.version,
        })
        resp.raise_for_status()

    def success(self, output):
        if self.dry_run:
            return
        resp = requests.post(self.update_status_url, data={
            'node_name': settings.NODE_NAME,
            'status': 'success',
            'source_url': self.source_url,
            'output': output,
            'client_version': self.version,
        })
        resp.raise_for_status()
