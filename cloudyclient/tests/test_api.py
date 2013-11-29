import os.path as op

from nose.tools import assert_equal

from cloudyclient.api import find_deployment_variables


DATA_DIR = op.join(op.dirname(__file__), 'data')


def test_find_deployment_variables():
    location = DATA_DIR
    assert_equal(find_deployment_variables(location), None)
    location = op.join(DATA_DIR, 'checkout_sample', '.project.0')
    assert_equal(find_deployment_variables(location), {'a': 1, 'b': 3})
    location = op.join(DATA_DIR, 'checkout_sample', '.project.0', 'subdir')
    assert_equal(find_deployment_variables(location), {'a': 1, 'b': 3})
