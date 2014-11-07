import os.path as op

from nose.tools import assert_equal, assert_raises, assert_not_equal

from cloudyclient.conf import CliConfig, search_up
from cloudyclient.exceptions import ConfigurationError


THIS_DIR = op.dirname(__file__)
DATA_DIR = op.join(THIS_DIR, 'data')


def test_search_up():
    assert_equal(search_up('.cloudy.yml', DATA_DIR),
            op.join(DATA_DIR, '.cloudy.yml'))


def test_cli_config():
    config = CliConfig(op.join(DATA_DIR, '.cloudy.yml'))
    assert_not_equal(len(config), 0)
    assert_raises(ConfigurationError, CliConfig, 'foo')
    assert_equal(config.deployment_groups, config['deployment_groups'])
