import os
import os.path as op

import yaml

from cloudyclient.exceptions import ConfigurationError


class CliConfig(dict):
    '''
    Reads and stores CLI configuration.
    '''

    def __init__(self, locations):
        if isinstance(locations, basestring):
            locations = [locations]
        for location in locations:
            if op.isfile(location):
                with open(location) as fp:
                    data = yaml.safe_load(fp)
                break
        else:
            raise ConfigurationError('configuration not found, '
                    'searched in: %s' % ', '.join(locations))
        super(CliConfig, self).__init__(data)


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
