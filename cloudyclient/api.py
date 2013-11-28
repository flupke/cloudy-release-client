import subprocess
import logging
import contextlib


logger = logging.getLogger(__name__)
_cwd_stack = []


def run(*cmd_args, **kwargs):
    '''
    Run a subprocess with the list of arguments *cmd_args*.

    Additional keyword arguments are passed to the :class:`subprocess.Popen`
    constructor.

    Returns the subprocess' stdout on success.

    Raises :class:`subprocess.CalledProcessError` if the command returns a
    non-zero exit status.
    '''
    cmd_string = ' '.join(cmd_args)
    logger.info(cmd_string)
    if _cwd_stack and 'cwd' not in kwargs:
        kwargs['cwd'] = _cwd_stack[-1]
    process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, **kwargs)
    stdout, stderr = process.communicate()
    if stdout:
        logger.info('stdout: %s', stdout)
    if stderr:
        logger.info('stderr: %s', stderr)
    retcode = process.poll()
    if retcode:
        error = subprocess.CalledProcessError(retcode, cmd_string)
        logger.error(str(error))
        raise error
    return stdout


@contextlib.contextmanager
def cd(path):
    '''
    A context manager that can be used to change the current working directory
    of processes started by :func:`run`.
    '''
    _cwd_stack.append(path)
    try:
        yield path
    finally:
        _cwd_stack.pop()
