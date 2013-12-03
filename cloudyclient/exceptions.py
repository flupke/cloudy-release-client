class CloudyException(Exception):
    '''
    Base class for all exceptions.
    '''


class TemplateError(Exception):
    '''
    Raised by :func:`cloudyclient.api.render_template`.
    '''
