import os.path as op


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
