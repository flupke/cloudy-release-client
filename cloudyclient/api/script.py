import os.path as op

from cloudyclient.conf.local import load_conf
from cloudyclient import log

from .virtualenv import VersionedVirtualenv
from .base import find_deployment_data, find_deployment_variables


class PythonDeployScript(object):
    '''
    Base class for standard python deployment scripts.

    Deployments using this script must at least define a ``venv_dir``
    deployment variable (the path to the virtualenv). If it contains "~", it
    will be expanded to the user's home directory.

    If *copied_system_packages* is used, the system python executable is used
    to retrieve system packages paths. By default the path to the system python
    executable is ``/usr/bin/python``. If needed it can be overridden with the
    ``sys_python`` deployment variable.
    '''

    requirements = []
    '''List of requirements files to install.'''

    use_wheel = False
    '''
    If true, install wheel in the virtualenv and install packages with
    --use-wheel (requires recent versions of pip and virtualenv to be installed
    on the system).
    '''

    no_deps = False
    '''If true, run pip with --no-deps.'''

    venv_class = VersionedVirtualenv
    '''
    Can be used in subclasses to change the virtualenv abstraction class.
    '''

    disable_venv_rollbacks = False
    '''
    If True, fast virtualenv rollbacks with git are disabled, and pip install
    is always called.

    This can be useful if there are multiple deployments participating to the
    same virtualenv, and a rollback may erase changes made by another
    deployment.
    '''

    copied_system_packages = []
    '''
    A list of Python package names that must be copied from the system
    installation to the deployment virtualenv (useful for packages difficult or
    impossible to install with pip such as PyQt4 or PyGTK).
    '''

    def __init__(self):
        # Setup logging
        load_conf()
        log.setup()
        # Load deployment variables and data
        self.ddata = find_deployment_data()
        if self.ddata is None:
            raise Exception('deployment state not found')
        self.dvars = find_deployment_variables()
        # Expand venv_dir
        self.dvars['venv_dir'] = op.expanduser(self.dvars['venv_dir'])

    def collect_requirements(self):
        '''
        Returns a list of requirements filenames to install.

        The default implementation returns the contents of
        :attr:`requirements`.
        '''
        return self.requirements

    def install_requirements(self):
        '''
        Install requirements (the list of filenames returned by
        :meth:`collect_requirements`) in the virtualenv.
        '''
        if self.use_wheel:
            self.venv.run('pip', 'install', 'wheel')
        reqs = self.collect_requirements()
        args = ['pip', 'install']
        for req in reqs:
            args.extend(['-r', req])
        if self.use_wheel:
            args.append('--use-wheel')
        if self.no_deps:
            args.append('--no-deps')
        self.venv.run(*args)

    def copy_system_packages(self):
        '''
        Copy packages defined in the :attr:`copied_system_packages` attribute
        into the virtualenv.
        '''
        for package in self.copied_system_packages:
            self.venv.copy_system_package(package,
                    sys_python=self.dvars.get('sys_python'))

    def setup_packages(self):
        '''
        Run the setup.py of the deployed code.

        The default implementation assumes a standard organization and runs
        ``setup.py install`` in the root directory. Reimplement this method in
        your subclass if have a non-standard layout or need to run more
        commands.
        '''
        self.venv.run('python', 'setup.py', 'install')

    def install(self):
        '''
        Do whatever needs to be done to install the deployed code (install
        configuration files, create work directories, etc...).

        The default implementation does nothing.
        '''

    def post_install(self):
        '''
        Run auxiliary actions after the installation (restart services, log
        deployment to external services, etc...).

        The default implementation does nothing.
        '''

    def run(self):
        '''
        Core structure of the script.
        '''
        # Create virtualenv
        self.venv = self.venv_class(self.dvars['venv_dir'])
        # Is this deployment a rollback?
        if (self.disable_venv_rollbacks or
                self.ddata['commit'] not in self.venv.releases()):
            # No, install requirements normally and save a snapshot of the
            # virtualenv
            self.venv.checkout_latest(clean=not self.disable_venv_rollbacks)
            self.install_requirements()
            self.copy_system_packages()
            snapshot = True
        else:
            # Yes, simply rollback virtualenv to the previous snapshot
            self.venv.rollback(self.ddata['commit'])
            snapshot = False
        # Always re-run setup_packages because their location changes at each
        # deployment, which could break setup.py develop
        self.setup_packages()
        if snapshot:
            self.venv.snapshot(self.ddata['commit'])
        # Run install and post install hooks
        self.install()
        self.post_install()
