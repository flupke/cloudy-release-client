import os
import os.path as op

import yaml

from cloudyclient.exceptions import ConfigurationError


CONFIG_FILENAME = '.cloudy.yml'


class CliConfig(dict):
    '''
    Retrieves CLI configuration data by searching ``.cloudy.yml`` in the
    current directory and in parent directories.
    '''

    def __init__(self, location=None):
        if location is None:
            location = os.getcwd()
        location = op.abspath(location)
        path = None
        while True:
            if CONFIG_FILENAME in os.listdir(location):
                path = op.join(location, CONFIG_FILENAME)
                break
            if location == '/':
                break
            location = op.split(location)[0]
        if path is None:
            raise ConfigurationError('"%s" not found in this directory '
                    'or in parent directories' % CONFIG_FILENAME)
        self.path = path
        with open(path) as fp:
            data = yaml.load(fp)
        super(CliConfig, self).__init__(data)
