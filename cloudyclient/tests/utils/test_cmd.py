import os
import os.path as op
import shutil
import threading
import uuid
import time
import logging

from nose.tools import assert_raises

from cloudyclient.utils.cmd import run_and_watch_tree
from cloudyclient.exceptions import CommandFailed


TMP_DIR = op.join(op.dirname(__file__), 'tmp')
logger = logging.getLogger(__name__)


def setup():
    if op.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.mkdir(TMP_DIR)


def test_run_and_watch_tree():
    run_and_watch_tree(['sleep', '1'], TMP_DIR, timeout=1.5, retries=1,
                       check_interval=0.1)


def test_run_and_watch_tree_timeout():
    with assert_raises(CommandFailed):
        run_and_watch_tree(['sleep', '1'], TMP_DIR, timeout=0.5, retries=1,
                           check_interval=0.1)


def test_run_and_watch_mtime_changes():
    touch_one = lambda: _touch_for(op.join(TMP_DIR, 'file'), 23, 0.1)
    thread = threading.Thread(target=touch_one)
    thread.start()
    run_and_watch_tree(['sleep', '2'], TMP_DIR, timeout=1.5, retries=1,
                       check_interval=0.1)
    thread.join()


def test_run_and_watch_files_change():
    touch_many = lambda: _touch_random(TMP_DIR, 13, 0.1)
    thread = threading.Thread(target=touch_many)
    thread.start()
    run_and_watch_tree(['sleep', '1'], TMP_DIR, timeout=0.5, retries=1,
                       check_interval=0.1)
    thread.join()


def _touch_for(path, times, interval):
    for i in range(times):
        _touch(path)
        time.sleep(interval)


def _touch_random(base_dir, times, interval):
    for i in range(times):
        path = op.join(base_dir, uuid.uuid4().hex)
        _touch(path)
        time.sleep(interval)


def _touch(path, times=None):
    with open(path, 'a'):
        os.utime(path, times)
