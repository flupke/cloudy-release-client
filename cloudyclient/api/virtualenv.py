import os.path as op

from .base import run, cd


class VersionedVirtualenv(object):
    '''
    A helper to build virtualenv versioned with git, allowing fast
    rollbacks, and fast updates.

    The virtualenv is built at *path* when the object is created, if *path*
    does not exist.

    If *system_site_packages* is True, --system-site-packages is passed to the
    ``virtualenv`` command. Access to system site packages can be changed on an
    existing virtualenv by passing True in *rerun_virtualenv*.
    '''

    def __init__(self, path, tags_prefix='release-',
            system_site_packages=False, rerun_virtualenv=False):
        self.path = path
        self.tags_prefix = tags_prefix
        self.system_site_packages = system_site_packages
        venv_exists = op.exists(self.path)
        venv_args = ['virtualenv', self.path]
        if not venv_exists or rerun_virtualenv:
            if system_site_packages:
                venv_args.append('--system-site-packages')
            else:
                venv_args.append('--no-site-packages')
            run(*venv_args)
        if not venv_exists:
            with cd(self.path):
                run('git', 'init')
                run('git', 'config', 'user.name', 'anonymous')
                run('git', 'config', 'user.email', 'a@a.com')
                run('git', 'add', '.')
                run('git', 'commit', '-qm', 'initial commit')

    def run(self, *cmd_args, **kwargs):
        '''
        Run a command in the virtualenv.

        The first item in *cmd_args* is joined with the ``bin/`` directory of
        this virtualenv.
        '''
        cmd_args = list(cmd_args)
        cmd_args[0] = op.join(self.path, 'bin', cmd_args[0])
        return run(*cmd_args, **kwargs)

    def snapshot(self, release):
        '''
        Take a snapshot of the virtualenv, named *release*.
        '''
        with cd(self.path):
            if run('git', 'status', '--porcelain', log_pipes=False):
                run('git', 'add', '--all', '.')
                run('git', 'commit', '-qam', 'release: %s' % release)
                run('git', 'tag', '-f', self.tags_prefix + release)

    def rollback(self, release):
        '''
        Revert the virtualenv to a previous release.
        '''
        tag_name = self.tags_prefix + release
        with cd(self.path):
            self.checkout(tag_name)

    def checkout_latest(self, clean=True):
        '''
        Checkout the latest release.
        '''
        with cd(self.path):
            self.checkout('master', clean=clean)

    def releases(self):
        '''
        Return the list of snapshoted releases in this virtualenv.
        '''
        with cd(self.path):
            tags = run('git', 'tag').split()
        releases = []
        for tag in tags:
            if tag.startswith(self.tags_prefix):
                releases.append(tag[len(self.tags_prefix):])
        return releases

    def copy_system_package(self, pkg, sys_python=None):
        '''
        Copy system-wide *pkg* in this virtualenv.

        *sys_python* can be given to customize the system python executable
        path. The default is '/usr/bin/python'.
        '''
        if sys_python is None:
            sys_python = '/usr/bin/python'
        # Get package path in the system packages
        pkg_file = run(sys_python, '-c',
                'import {0}; print {0}.__file__'.format(pkg))
        # Get site-packages path in the virtualenv
        venv_site_packages = self.run('python', '-c',
            'from distutils.sysconfig import get_python_lib; print(get_python_lib())')
        # Copy package in virtualenv
        if '__init__.py' in pkg_file:
            # Dealing with a package
            src_dir = op.dirname(pkg_file)
            basename = op.basename(src_dir)
            dst_dir = op.join(venv_site_packages, basename)
            if op.exists(dst_dir):
                run('rm', '-rf', dst_dir)
            run('cp', '-rL', src_dir, dst_dir)
        else:
            # Dealing with a top-level module
            run('cp', '-L', pkg_file, venv_site_packages)

    def checkout(self, name, clean=True):
        '''
        Checkout *name*.

        If *clean* is true, also run git clean to remove extra files.
        '''
        args = ['git', 'checkout']
        if clean:
            args.append('-f')
        args.append(name)
        run(*args)
        if clean:
            run('git', 'clean', '-fxdq')

