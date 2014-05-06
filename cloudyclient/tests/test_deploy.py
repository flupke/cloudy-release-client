import os
import os.path as op
import shutil

from nose import with_setup
from nose.tools import assert_equal

from cloudyclient.deploy import DeploymentScript


THIS_DIR = op.abspath(op.dirname(__file__))
TMP_DIR = op.join(THIS_DIR, 'tmp')
DATA_DIR = op.join(THIS_DIR, 'data')


def setup_func():
    if op.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)


@with_setup(setup_func)
def test_bash_script_funky_line_endings():
    script = DeploymentScript('bash', 'touch foo\r\ntouch bar')
    script.run(TMP_DIR)
    assert_equal(set(os.listdir(TMP_DIR)), {'foo', 'bar'})


@with_setup(setup_func)
def test_bash_script_with_deploy_vars():
    script = DeploymentScript('bash',
            'touch {0}/$a\ntouch {0}/$b'.format(TMP_DIR))
    script.run(op.join(DATA_DIR, 'checkout_sample', '.project-shell-with-base-vars.0'))
    assert_equal(set(os.listdir(TMP_DIR)), {'1', '2'})
