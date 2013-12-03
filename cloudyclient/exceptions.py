class CloudyException(Exception):
    '''
    Base class for all exceptions.
    '''


class CloudyTemplateError(Exception):
    '''
    Raised by :func:`cloudyclient.api.render_template`.
    '''
