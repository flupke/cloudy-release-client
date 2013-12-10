import os.path as op

from nose.tools import assert_equal, assert_raises, assert_not_equal

from cloudyclient.cli.config import CliConfig
from cloudyclient.exceptions import ConfigurationError


DATA_DIR = op.join(op.dirname(__file__), 'data')


def test_cli_config():
    config = CliConfig(DATA_DIR)
    assert_not_equal(len(config), 0)
    config_2 = CliConfig(op.join(DATA_DIR, 'checkout_sample'))
    assert_equal(config, config_2)
    assert_raises(ConfigurationError, CliConfig, op.join(DATA_DIR, '..'))
