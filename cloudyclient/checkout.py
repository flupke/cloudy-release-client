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
                return func()
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

    def get_commit(self, base_dir, project_name, repo_url, commit):
        '''
        Checkout a specific commit from VCS.
        '''
        # Create base directory
        run('mkdir', '-p', base_dir)
        # Clone the repository or copy it to its next location
        checkout_symlink = op.join(base_dir, project_name)
        checkout_dirs = [checkout_symlink + '.%s' % i for i in range(2)]
        if not op.exists(checkout_symlink):
            # First checkout
            next_checkout_dir = checkout_dirs[0]
            if op.exists(next_checkout_dir):
                run('rm', '-rf', next_checkout_dir)
            self.clone(repo_url, next_checkout_dir)
            update_symlink = False
        else:
            # n-th checkout
            current_checkout_dir = run('readlink', checkout_symlink)
            _, index = op.splitext(current_checkout_dir)
            index = int(index[1:])
            next_checkout_dir = checkout_dirs[(index + 1) % 2]
            run('rm', '-rf', next_checkout_dir)
            run('cp', '-r', current_checkout_dir, next_checkout_dir)
            update_symlink = True
        # Fetch from VCS and checkout commit
        with cd(next_checkout_dir):
            self.fetch()
            self.checkout_commit(commit)
            self.clean()
        # Create or update the checkout symlink
        if update_symlink:
            temp_symlink = '%s.new' % checkout_symlink
            run('ln', '-s', next_checkout_dir, temp_symlink)
            run('mv', '-T', temp_symlink, checkout_symlink)
        else:
            run('ln', '-s', next_checkout_dir, checkout_symlink)

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
        run('git', 'clean', '-fxd')


register('git', GitCheckout)
