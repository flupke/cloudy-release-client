import os
import os.path as op
import time

from cloudyclient.api import run, wait_process
from ..exceptions import Timeout


def safe_git_operation(args,
                       retries=5,
                       timeout=60,
                       check_interval=0.25):
    '''
    Execute a git *command* with *args*, making sure it doesn't get stuck.

    Example::

        safe_git_operation(['git', 'fetch'])

    '''
    for i in range(retries):
        try:
            return _run_git_cmd_once(args, timeout, check_interval)
        except Timeout:
            pass
    else:
        raise Exception('git fetch failed after %s retries' % retries)


def _get_tree_data(base_dir):
    ret = {
        'dirs': {},
        'files': set()
    }
    for root, dirs, files in os.walk(base_dir):
        ret['dirs'][root] = {f: op.getmtime(op.join(root, f)) for f in files}
        ret['files'].update(op.join(root, f) for f in files)
    return ret


def _compare_tree_data(prev_data, new_data):
    if prev_data['files'] != new_data['files']:
        additions = new_data['files'].difference(prev_data['files'])
        deletions = prev_data['files'].difference(new_data['files'])
        return True, '%s additions, %s deletions' % (len(additions),
                                                     len(deletions))
    for root, prev_files in prev_data['dirs'].items():
        new_files = new_data['dirs'][root]
        for name, prev_mtime in prev_files.items():
            new_mtime = new_files[name]
            if prev_mtime != new_mtime:
                return True, '%s mtime changed' % op.join(root, name)
    return False, 'tree did not change'


def _run_git_cmd_once(args, timeout, check_interval):
    process = run(*args, block=False)
    last_change = time.time()
    watched_dir = '.git'
    prev_data = _get_tree_data(watched_dir)
    while True:
        if process.poll() is not None:
            break
        time.sleep(check_interval)
        new_data = _get_tree_data(watched_dir)
        changed, _ = _compare_tree_data(prev_data, new_data)
        if changed:
            last_change = time.time()
        else:
            if time.time() - last_change > timeout:
                process.terminate()
                process.wait()
                raise Timeout()
        prev_data = new_data
    # Call wait_process() to log streams and raise an error if process
    # terminated abnormally
    return wait_process(process)
