import os
import os.path as op
import shutil

from nose.tools import assert_equal

from cloudyclient.deploy import DeploymentScript


THIS_DIR = op.dirname(__file__)
TMP_DIR = op.join(THIS_DIR, 'tmp')


def setup():
    if op.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)


def test_bash_script_funky_line_endings():
    script = DeploymentScript('bash', 'touch foo\r\ntouch bar')
    script.run(TMP_DIR)
    assert_equal(os.listdir(TMP_DIR), ['foo', 'bar'])
