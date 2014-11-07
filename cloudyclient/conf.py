import os
import os.path as op
import socket

import yaml

from cloudyclient.exceptions import ConfigurationError


DEFAULT_CONFIG_LOCATIONS = [
    "~/.config/cloudy/client.yml",
    "/etc/cloudy/client.yml",
]
DEFAULTS = {
    # The list of deployment poll urls from which the client gets its
    # configurations
    'poll_urls': [],

    # Number of times vcs commands are retried before failing
    'vcs_retries': 10,

    # Deployments poll interval in seconds
    'poll_interval': 3,

    # Client requests settings
    'requests_timeout': 10,
    'requests_retries': 3,
    'requests_pool_size': 30,

    # The name used to identify this node in the cloudy-release server
    'node_name': socket.getfqdn(),

    # Default format for all loggers
    'logs_format': '[%(asctime)s] [%(levelname)s] %(message)s',

    # Authentication
    'secret': None,
}


def load_conf(locations=None):
    """
    Load local configuration.

    *configs* can be a list of Python file locations that will be loaded in
    order to update the defaults.
    """
    if locations is None:
        locations = DEFAULT_CONFIG_LOCATIONS
    settings.update(CliConfig(locations))


class CliConfig(dict):
    '''
    Parses and stores CLI configuration.
    '''

    def __init__(self, locations=None, data=None):
        if data is None:
            if isinstance(locations, basestring):
                locations = [locations]
            for location in locations:
                location = op.expanduser(location)
                if op.isfile(location):
                    with open(location) as fp:
                        data = yaml.safe_load(fp)
                    break
            else:
                raise ConfigurationError('configuration not found, '
                        'searched in: %s' % ', '.join(locations))
        super(CliConfig, self).__init__(data)

    def __getattr__(self, name):
        return self[name]


def search_up(filename, location=None):
    '''
    Search for *filename* in *location* and its parents.

    If *location is None, search from the current directory.

    Return the location or None if there is no such file.
    '''
    if location is None:
        location = os.getcwd()
    location = op.abspath(location)
    while location != '/':
        if filename in os.listdir(location):
            return op.join(location, filename)
        location = op.split(location)[0]


settings = CliConfig(data=DEFAULTS)
