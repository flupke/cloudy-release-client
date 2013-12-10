class CloudyException(Exception):
    '''
    Base class for all exceptions.
    '''


class TemplateError(CloudyException):
    '''
    Raised by :func:`cloudyclient.api.render_template`.
    '''


class ConfigurationError(CloudyException):
    pass
