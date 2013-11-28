import logging
import contextlib
from logging import FileHandler
from logging.handlers import BufferingHandler

from cloudyclient.conf import settings
from cloudyclient.state import get_log_filename


@contextlib.contextmanager
def add_hanlers(*handlers):
    '''
    Temporarily add handlers to the root logger.
    '''
    logger = logging.getLogger()
    for handler in handlers:
        if handler is not None:
            logger.addHandler(handler)
    try:
        yield
    finally:
        for handler in handlers:
            if handler is not None:
                logger.removeHandler(handler)


def get_formatter():
    '''
    Get the default formatter for all handlers.
    '''
    return logging.Formatter(settings.LOGS_FORMAT)


class FormattedMemoryHandler(BufferingHandler):
    '''
    Simple subclass of :class:`logging.handlers.BufferingHandler` that stores
    formatted messages in a buffer.
    '''

    def __init__(self):
        BufferingHandler.__init__(self, 0)

    def emit(self, record):
        self.buffer.append(self.format(record))

    def value(self):
        '''
        Get all buffered logs as a string.
        '''
        return '\n'.join(self.buffer)


def setup():
    '''
    Setup the root logger.
    '''
    formatter = get_formatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)


def get_deployment_handlers(base_dir, project_name):
    '''
    Make a pair of logging handlers for a particular deployment.

    Returns a tuple containing the :class:`logging.FileHandler` and the
    :class:`FormattedMemoryHandler` objects prepared for the deployment
    *project_name* in *base_dir*.
    '''
    formatter = get_formatter()
    try:
        file_handler = FileHandler(get_log_filename(base_dir, project_name))
        file_handler.setFormatter(formatter)
    except IOError:
        # This can fail in dry run mode because state directory was not created
        file_handler = None
    mem_handler = FormattedMemoryHandler()
    mem_handler.setFormatter(formatter)
    return file_handler, mem_handler
