import os.path as op
import logging

import requests

from cloudyclient.conf import settings


logger = logging.getLogger(__name__)


class CloudyClient(object):
    '''
    Encapsulates communications with the cloudy-release server.
    '''

    def __init__(self, poll_url):
        self.poll_url = poll_url

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
        resp = requests.post(self.update_status_url, data={
            'node_name': settings.NODE_NAME,
            'status': 'pending',
            'source_url': self.source_url,
        })
        resp.raise_for_status()

    def error(self, output):
        resp = requests.post(self.update_status_url, data={
            'node_name': settings.NODE_NAME,
            'status': 'error',
            'source_url': self.source_url,
            'output': output,
        })
        resp.raise_for_status()

    def success(self, output):
        resp = requests.post(self.update_status_url, data={
            'node_name': settings.NODE_NAME,
            'status': 'success',
            'source_url': self.source_url,
            'output': output,
        })
        resp.raise_for_status()
