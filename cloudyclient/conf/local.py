from cloudyclient import conf
from cloudyclient.conf import defaults


DEFAULT_CONFIG_PLACES = [
    "~/.config/cloudy/client.conf.py",
    "/etc/cloudy/client.conf.py",
]


def load_conf(configs=None, quiet=True):
    """
    Load local configuration.

    *configs* can be a list of Python file locations that will be loaded in
    order to update the defaults.
    """
    if configs is None:
        configs = DEFAULT_CONFIG_PLACES
    conf.load(defaults=defaults, configs=configs, log=not quiet)
