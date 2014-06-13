import collections


class ShellVariables(collections.Mapping):
    '''
    A container for shell script variables.

    Used in :func:`cloudyclient.api.base.find_deployment_variables` to support
    dummy inheritance.
    '''

    def __init__(self, data):
        self.data = data.replace('\r\n', '\n')

    def update(self, other):
        if not isinstance(other, ShellVariables):
            raise TypeError("can't mix shell variables with other types")
        self.data += '\n' + other.data

    def __unicode__(self):
        return self.data + '\n'

    def __nonzero__(self):
        return bool(self.data.strip())

    def _not_implemented(self, *args, **kwargs):
        raise NotImplementedError()

    __getitem__ = _not_implemented
    __iter__ = _not_implemented
    __len__ = _not_implemented
