import sys
import os
import os.path as op
import subprocess
import logging
import contextlib
import threading
import json
import traceback

import yaml
import jinja2

from cloudyclient.state import load_data
from cloudyclient.exceptions import TemplateError


logger = logging.getLogger(__name__)
_globals = threading.local()
no_default = object()


def get_global(name, default=no_default):
    '''
    Get a global variable by *name*.

    If *default* is specified, initialize the global with this value if if does
    not exist already.
    '''
    if default is not no_default:
        return _globals.__dict__.setdefault(name, default)
    return _globals.__dict__[name]


def set_global(name, value):
    '''
    Set global variable *name* to *value*.
    '''
    _globals.__dict__[name] = value


def run(*cmd_args, **kwargs):
    '''
    Run a subprocess with the list of arguments *cmd_args*.

    Additional keyword arguments are passed to the :class:`subprocess.Popen`
    constructor.

    Returns the subprocess' stdout on success, or raises
    :class:`subprocess.CalledProcessError` if the command returns a non-zero
    exit status.
    '''
    cmd_string = ' '.join(cmd_args)
    logger.info(cmd_string)
    if get_global('dry_run', False):
        return ''
    cwd_stack = get_global('cwd_stack', [])
    if cwd_stack and 'cwd' not in kwargs:
        kwargs['cwd'] = cwd_stack[-1]
    process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, **kwargs)
    stdout, stderr = process.communicate()
    stdout = stdout.strip()
    stderr = stderr.strip()
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
    logger.info('cd %s', path)
    cwd_stack = get_global('cwd_stack', [])
    cwd_stack.append(path)
    try:
        yield 
    finally:
        cwd_stack.pop()
        if cwd_stack:
            cwd = cwd_stack[-1]
        else:
            cwd = os.getcwd()
        logger.info('cd %s', cwd)


@contextlib.contextmanager
def dry_run():
    '''
    A context manager that inhibits :func:`run` from running any subprocess
    during its lifetime.
    '''
    set_global('dry_run', True)
    try:
        yield
    finally:
        set_global('dry_un', False)


def find_deployment_data(base_dir=None):
    '''
    Retrieve deployment data by searching from *base_dir* and up.

    If *base_dir* is not specified, :func:`os.getcwd` is used.

    Returns the data dict, or None if it was not found.
    '''    
    if base_dir is None:
        base_dir = os.getcwd()
    base_dir = op.abspath(base_dir)
    while base_dir != '/':
        base_dir, tail = op.split(base_dir)
        project_name, _, index = tail.rpartition('.')
        project_name = project_name.lstrip('.')
        if index.isdigit():
            # Looks like we found a checkout dir, see if we can load data
            data = load_data(base_dir, project_name)
            if data:
                return data


def find_deployment_variables(base_dir=None):
    '''
    Retrieve deployment variables by searching from *base_dir* and up.

    If *base_dir* is not specified, :func:`os.getcwd` is used.

    Returns the variables dict, or None if it was not found.
    '''
    data = find_deployment_data(base_dir=base_dir)
    if data is not None:
        variables_format = data['variables_format']
        variables = data['variables']
        if variables_format == 'json':
            return json.loads(variables)
        elif variables_format == 'yaml':
            return yaml.load(variables)
        elif variables_format == 'python':
            code = compile(variables, '<deployment variables>', 'exec')
            code_globals = {}
            exec(code, code_globals)
            code_globals.pop('__builtins__', None)
            return code_globals
        else:
            raise ValueError('unknwon variables format "%s"' %
                    variables_format)


def render_template(source, destination, context={}, use_jinja=False):
    '''
    Render template file *source* to *destination*.

    The contents of the source file are formatted with *context*, passed to the
    :meth:`basestring.format` method, or to jinja if *use_jinja* is True.
    '''
    # Read template source 
    with open(source) as fp:
        template_src = fp.read()

    # Render template
    if use_jinja:
        template = jinja2.Template(template_src, undefined=jinja2.StrictUndefined)
        try:
            rendered = template.render(**context)
        except jinja2.TemplateSyntaxError as exc:
            line = traceback.extract_tb(sys.exc_info()[2])[-1][1]
            context = _get_template_context(template_src, line)
            error = '{0}; line {1} in template:\n\n{2}'.format(
                    exc, line, context)
            raise TemplateError(error)
        except jinja2.UndefinedError:
            line = traceback.extract_tb(sys.exc_info()[2])[-1][1]
            context = _get_template_context(template_src, line)
            error = 'Undefined jinja variable; line {0} in template\n\n{1}'.format(
                    line, context)
            raise TemplateError(error)
    else:
        rendered = template_src.format(**context)

    # Save rendered template to destination
    with open(destination, 'w') as fp:
        fp.write(rendered)  


def _get_template_context(template, line, num_lines=5):
    '''
    Returns debugging context around a line in a given template.

    Returns:: string
    '''
    marker = '    <======================'
    template_lines = template.splitlines()
    num_template_lines = len(template_lines)

    # in test, a single line template would return a crazy line number like,
    # 357.  do this sanity check and if the given line is obviously wrong, just
    # return the entire template
    if line > num_template_lines:
        return template

    context_start = max(0, line - num_lines - 1)  # subtract 1 for 0-based indexing
    context_end = min(num_template_lines, line + num_lines)
    error_line_in_context = line - context_start - 1  # subtract 1 for 0-based indexing

    buf = []
    if context_start > 0:
        buf.append('[...]')
        error_line_in_context += 1

    buf.extend(template_lines[context_start:context_end])

    if context_end < num_template_lines:
        buf.append('[...]')

    if marker:
        buf[error_line_in_context] += marker

    return '---\n{0}\n---'.format('\n'.join(buf))        
