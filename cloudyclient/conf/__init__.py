'''
A flexible settings system based on Python files.
'''
import sys
import re
import os.path as op
from copy import deepcopy
import functools
from contextlib import contextmanager
import errno


dotted_path_pattern = re.compile(
    '^([a-zA-Z_][a-zA-Z_0-9]*\.)*[a-zA-Z_][a-zA-Z_0-9]*$')

# Reserved settings names
RESERVED_NAMES = (
    'get',
    '_clear',
    '_copy_attrs',
    '_loaded_attrs',
    '_push',
    '_pop',
    '_stack',
    '_as_dict',
)


class ConfigurationError(Exception):
    '''
    Raided to indicate errors at load time.
    '''


class InvalidNamespace(ConfigurationError):
    '''
    Raised when trying to access an invalid namespace.
    '''


class SettingsContainer(object):
    '''
    An object storing settings, constructed by combining defaults with
    user-provided configuration.

    Defaults are specified by passing one or more objects as positional
    arguments.
    '''

    def __init__(self):
        self._loaded_attrs = set()
        self._stack = []

    def _clear(self):
        '''
        Clear the attributes that were copied in this object by
        :meth:`_copy_attrs`.
        '''
        for attr in self._loaded_attrs.copy():
            delattr(self, attr)

    def _copy_attrs(self, src, context_name=None):
        '''
        Copy attributes of *src* into this object.
        '''
        for name in dir(src):
            if name.startswith('__') and name.endswith('__'):
                continue
            if name in RESERVED_NAMES:
                if context_name:
                    raise ConfigurationError('while loading %s: "%s" is a '
                            'reserved name' % (context_name, name))
                else:
                    raise ConfigurationError('while loading %r: "%s" is a '
                            'reserved name' % (src, name))
            setattr(self, name, getattr(src, name))
            self._loaded_attrs.add(name)

    def get(self, name, default=None):
        '''
        Get attribute named *name*. If there is no attribute of that name in
        this object, return *default*.
        '''
        return getattr(self, name, default)

    def _push(self):
        data = deepcopy(self.__dict__)
        del data['_stack']
        self._stack.append(data)

    def _pop(self):
        stack = self._stack
        self.__dict__ = stack.pop(-1)
        self._stack = stack

    def _as_dict(self):
        ret = {}
        for name in self._loaded_attrs:
            attr = getattr(self, name)
            if isinstance(attr, SettingsContainer):
                ret[name] = attr._as_dict()
            else:
                ret[name] = attr
        return ret

    def __delattr__(self, name):
        super(SettingsContainer, self).__delattr__(name)
        self._loaded_attrs.remove(name)


def load(configs=None, defaults=None, namespace=None, log=False):
    '''
    Fill the global :attr:`settings` object, first with *defaults* then with
    *configs*.

    *configs* is a list of Python file locations. They are tried one by one,
    stopping at the first location that can be successfully loaded.

    *defaults* is a list of Python file location or objects (class instances,
    modules, etc...), that are all loaded one by one. Passing a file location
    that does not exist raises an error.

    You may specify a single item instead of lists for *configs* and *defaults*.

    You can specify *namespace* to store the settings in a particular
    namespace. For example ``conf.load('/path/to/conf.py', namespace='foo')``
    will make the settings accessible in the ``conf.settings.foo`` namespace.

    If *log* is true, print informations about what is loaded.
    '''
    # Check parameters
    if configs is None and defaults is None:
        raise ValueError('you must specify locations or defaults')
    # Get or create the namespace's settings
    if namespace is None:
        settings_obj = settings
    else:
        if not dotted_path_pattern.match(namespace):
            raise ValueError('invalid namespace format "%s"' % namespace)
        parts = namespace.split('.')
        settings_obj = settings
        for i, part in enumerate(parts):
            if not hasattr(settings_obj, part):
                setattr(settings_obj, part, SettingsContainer())
                settings_obj._loaded_attrs.add(part)
            else:
                if not isinstance(getattr(settings_obj, part), SettingsContainer):
                    raise ConfigurationError('creating namespace would '
                            'overwrite the "settings.%s" setting' %
                            '.'.join(part[:i]))
            settings_obj = getattr(settings_obj, part)
    # Load defaults and configurations
    if defaults is not None:
        _load(settings_obj, smart_list(defaults), load_all=True)
    if configs is not None:
        expanded_configs = [op.expanduser(p) if isinstance(p, basestring) else p
                for p in smart_list(configs)]
        _load(settings_obj, expanded_configs, ignore_missing=True, log=log,
                namespace=namespace)


def _load(settings_obj, locations, ignore_missing=False, load_all=False,
        log=False, namespace=None):
    for location in locations:
        if isinstance(location, basestring):
            if op.exists(location):
                # Import config with execfile()
                globals_ = {'__file__': location}
                with open(location) as fp:
                    code = compile(fp.read(), location, 'exec')
                exec(code, globals_)
                tmp = _DummyContainer()
                for name, value in globals_.items():
                    setattr(tmp, name, value)
                settings_obj._copy_attrs(tmp, location)
                if log:
                    msg = 'Loaded configuration from %s' % location
                    if namespace is not None:
                        msg += ' into %s' % namespace
                    try:
                        print >> sys.stderr, msg
                    except IOError as err:
                        # In rare cases we can get a broken pipe error here
                        # (probably related to supervisord) avoid breaking
                        # everything because of it.
                        if err.errno != errno.EPIPE:
                            raise
                if not load_all:
                    break
            elif not ignore_missing:
                raise ConfigurationError('file "%s" not found' % location)
        else:
            settings_obj._copy_attrs(location)
            if not load_all:
                break


def clear(namespace=None):
    '''
    Clear all settings. *namespace* may be specified to clear only a specific
    namespace.
    '''
    if namespace is None:
        settings_obj = settings
    else:
        if not dotted_path_pattern.match(namespace):
            raise ValueError('invalid namespace format "%s"' % namespace)
        parts = namespace.split('.')
        settings_obj = settings
        for part in parts:
            settings_obj = getattr(settings_obj, part)
    settings_obj._clear()


def smart_list(value):
    '''
    Convert *value* to a single item list if it is a string or not an iterable.
    '''

    def is_iterable(value):
        try:
            iter(value)
            return True
        except TypeError:
            return False

    if (isinstance(value, basestring) or not is_iterable(value)):
        return [value]
    return value


class _DummyContainer(object):

    pass


def push():
    '''
    Save current settings.
    '''
    settings._push()


def pop():
    '''
    Restore settings previously saved with :func:`push`
    '''
    settings._pop()


def as_dict(settings_obj=None):
    '''
    Return *settings_obj* contents in a dictionnary (use root settings if left
    unspecified).

    Namespace settings are included as nested dicts.
    '''
    if settings_obj is None:
        settings_obj = settings
    return settings_obj._as_dict()


def with_settings(new_settings):
    '''
    A decorator to temporarily replace settings. *new_settings* has the same
    format as for :func:`replace_settings`.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with replace_settings(new_settings):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextmanager
def replace_settings(new_settings):
    '''
    A context manager to replace settings. *new_settings* must be a mapping
    containing the path of the settings to replace and their new value, e.g.::

        from stupeflix.conf import settings, replace_settings

        with replace_settings({'foo.bar.SETTING': 10}):
            assert settings.foo.bar.SETTING == 10
    '''
    push()
    for setting, value in new_settings.items():
        container = settings
        if '.' in setting:
            path, setting = setting.rsplit('.', 1)
            path_parts = path.split('.')
            while path_parts:
                try:
                    container = getattr(container, path_parts.pop(0))
                except AttributeError:
                    raise InvalidNamespace(path)
        setattr(container, setting, value)
    try:
        yield
    finally:
        pop()


settings = SettingsContainer()

