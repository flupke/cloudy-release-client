import os.path as op
import os
import logging
import json


logger = logging.getLogger(__name__)


def get_state_directory(base_dir, project_name):
    '''
    Build the state directory path from *base_dir* and *project_name*.
    '''
    return op.join(base_dir, '.%s.state' % project_name)


def get_data_filename(base_dir, project_name):
    '''
    Get the filename of the data file in the state directory.
    '''
    state_dir = get_state_directory(base_dir, project_name)
    return op.join(state_dir, 'data.json')


def get_log_filename(base_dir, project_name):
    '''
    Get the per-deployment log filename in the state directory.
    '''
    state_dir = get_state_directory(base_dir, project_name)
    return op.join(state_dir, 'deployment.log')


def load_data(base_dir, project_name):
    '''
    Load data from the state directory.

    Returns the data dict or an empty dict if it's corrupt or inexistant.
    '''
    filename = get_data_filename(base_dir, project_name)
    if op.exists(filename):
        with open(filename) as fp:
            try:
                return json.load(fp)
            except:
                logger.error('corrupt data file "%s"', filename, exc_info=True)
                os.unlink(filename)
    return {}
