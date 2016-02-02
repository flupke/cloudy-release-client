import os
import os.path as op
import time
import logging

from cloudyclient.api import run, wait_process
from ..exceptions import Timeout, CommandFailed


logger = logging.getLogger(__name__)


def run_and_watch_tree(args,
                       watched_dir,
                       retries=5,
                       timeout=60,
                       check_interval=0.25):
    '''
    Execute a command with *args* while monitoring the files in *watched_dir*.

    If files stop changing in *watched_dir* for more than *timeout* seconds,
    kill the command and retry, up to *retries* times. The files in *base_dir*
    are checked every *check_interval* seconds.

    Example::

        run_and_watch_tree(['git', 'fetch'], '.git')

    '''
    cmd_string = ' '.join(args)
    for i in range(retries):
        try:
            return _run_and_watch_tree_once(args, watched_dir, timeout,
                                            check_interval)
        except Timeout:
            logger.warning('"%s" timed out', cmd_string)
    else:
        err = '"%s" failed after %s retries' % (cmd_string, retries)
        logger.error(err)
        raise CommandFailed(err)


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


def _run_and_watch_tree_once(args, watched_dir, timeout, check_interval):
    cmd_string = ' '.join(args)
    process = run(*args, block=False)
    last_change = time.time()
    prev_data = _get_tree_data(watched_dir)
    while True:
        if process.poll() is not None:
            logger.debug('"%s" ended', cmd_string)
            break
        time.sleep(check_interval)
        new_data = _get_tree_data(watched_dir)
        changed, reason = _compare_tree_data(prev_data, new_data)
        if changed:
            last_change = time.time()
            logger.debug('files in %s changed: %s', watched_dir, reason)
        else:
            logger.debug('files did not change in %s', watched_dir)
            if time.time() - last_change > timeout:
                process.terminate()
                process.wait()
                raise Timeout()
        prev_data = new_data
    # Call wait_process() to log streams and raise an error if process
    # terminated abnormally
    logger.debug('retrieving "%s" streams', cmd_string)
    ret = wait_process(process)
    logger.debug('"%s" ended successfully', cmd_string)
    return ret
