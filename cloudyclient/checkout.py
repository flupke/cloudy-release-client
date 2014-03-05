import os.path as op
import functools
import subprocess
import time
import abc

from cloudyclient.api import run, cd
from cloudyclient.conf import settings


_registry = {}


def register(name, implementation):
    '''
    Register the :class:`Checkout` *implementation* under *name*.
    '''
    if name in _registry:
        raise ValueError('%s is already registered for name %s' %
                (_registry[name], name))
    _registry[name] = implementation


def get_implementation(name):
    '''
    Retrieve the :class:`Checkout` implementation named *name* or raise a
    :class:`KeyError` if there is no such implementation.
    '''
    try:
        return _registry[name]
    except KeyError:
        raise KeyError('unknown Checkout implementation "%s"' % name)


def rety_vcs_command(func):
    '''
    A decorator to wrap VCS commands, retrying ``settings.VCS_RETRIES`` times
    if the command returns with a non-zero exit status.
    '''

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        while True:
            try:
                return func(*args, **kwargs)
            except subprocess.CalledProcessError:
                retries += 1
                if retries >= settings.VCS_RETRIES:
                    raise
            time.sleep(1)

    return wrapper


class Checkout(object):
    '''
    Abstract base class for VCS checkouts.
    '''

    __metaclass__ = abc.ABCMeta

    def __init__(self, base_dir, project_name, repo_url, commit):
        self.base_dir = base_dir
        self.project_name = project_name
        self.repo_url = repo_url
        self.commit = commit
        self.checkout_symlink = op.join(base_dir, project_name)
        self.checkout_dirs = [op.join(base_dir, '.%s.%s' % (project_name, i))
                for i in range(2)]
        if not op.exists(self.checkout_symlink):
            self.next_checkout_dir = self.checkout_dirs[0]
            self.update_symlink = False
        else:
            self.current_checkout_dir = run('readlink', self.checkout_symlink)
            _, index = op.splitext(self.current_checkout_dir)
            index = int(index[1:])
            self.next_checkout_dir = self.checkout_dirs[(index + 1) % 2]
            self.update_symlink = True

    def get_commit(self):
        '''
        Checkout a specific commit from VCS.

        Returns the directory where the code has been checked out.
        '''
        # Create base directory
        run('mkdir', '-p', self.base_dir)
        # Clone the repository or copy it to its next location
        if not op.exists(self.checkout_symlink):
            # First checkout
            if op.exists(self.next_checkout_dir):
                run('rm', '-rf', self.next_checkout_dir)
            self.clone(self.repo_url, self.next_checkout_dir)
        else:
            # n-th checkout
            run('rm', '-rf', self.next_checkout_dir)
            run('cp', '-r', self.current_checkout_dir, self.next_checkout_dir)
        # Fetch from VCS and checkout commit
        with cd(self.next_checkout_dir):
            self.update_repo_url(self.repo_url)
            self.fetch()
            self.checkout_commit(self.commit)
            self.clean()
        return self.next_checkout_dir

    def finalize_commit(self):
        # Create or update the checkout symlink
        if self.update_symlink:
            temp_symlink = '%s.new' % self.checkout_symlink
            run('ln', '-s', self.next_checkout_dir, temp_symlink)
            run('mv', '-T', temp_symlink, self.checkout_symlink)
        else:
            run('ln', '-s', self.next_checkout_dir, self.checkout_symlink)

    @abc.abstractmethod
    def clone(self, repo_url, path):
        '''
        Clone *repo_url* from VCS into *path*.
        '''

    @abc.abstractmethod
    def fetch(self):
        '''
        Fetch code from VCS in an existing checkout.
        '''

    @abc.abstractmethod
    def checkout_commit(self, commit):
        '''
        Checkout *commit* in an existing checkout.
        '''

    @abc.abstractmethod
    def clean(self):
        '''
        Cleanup an existing checkout.
        '''

    @abc.abstractmethod
    def update_repo_url(self, url):
        '''
        Update the repository URL.
        '''


class GitCheckout(Checkout):

    @rety_vcs_command
    def clone(self, repo_url, path):
        run('git', 'clone', repo_url, path)

    @rety_vcs_command
    def fetch(self):
        run('git', 'fetch')

    def checkout_commit(self, commit):
        run('git', 'checkout', commit)

    def clean(self):
        run('git', 'clean', '-fxdq')

    def update_repo_url(self, url):
        run('git', 'remote', 'set-url', 'origin', url)


register('git', GitCheckout)
