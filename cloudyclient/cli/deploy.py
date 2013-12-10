'''
``cloudy deploy`` implementation.
'''
import sys
import logging

import requests

from cloudyclient.api import run
from cloudyclient.exceptions import ConfigurationError
from cloudyclient.client import CloudyClient
from cloudyclient.cli.config import CliConfig


def deploy(args):
    '''
    Get or set a deployment's commit.
    '''
    # Check args
    if not args.group and not args.list:
        print 'you must specify a group name or --list'
        sys.exit(1)

    # Inhibit API logging 
    api_logger = logging.getLogger('cloudyclient.api.base')
    api_logger.setLevel(logging.WARNING)

    # Load CLI configuration
    try:
        config = CliConfig()
    except ConfigurationError as exc:
        print exc
        sys.exit(1)

    if not args.list:
        push_commit(args, config)
    else:
        list_groups(args, config)


def push_commit(args, config):
    # Get deployment group definition from configuration
    deployment_groups = config.get('deployment_groups', {})
    group = deployment_groups.get(args.group)
    if group is None:
        print 'no such deployment group "%s"' % args.group
        sys.exit(1)
    
    # Retrieve the commit to deploy
    branch = group.get('branch')
    if branch is None:
        print '"branch" key missing from deployment group "%s"' % args.group
        sys.exit(1)
    if branch == '__current__':
        branch = current_git_branch()
    commit = run('git', 'rev-parse', branch)

    # Push changes if configuration asks for it
    push = group.get('push', False)
    if push:
        print 'git push'
        run('git', 'push', no_pipes=True)
        print
    push_tags = group.get('push_tags', False)
    if push_tags:
        print 'git push --tags'
        run('git', 'push', '--tags', no_pipes=True)
        print

    # Update deployments commits
    poll_urls = group.get('deployments')
    if not poll_urls:
        print 'deployment group "%s" defines no deployments' % args.group
    for url in poll_urls:
        client = CloudyClient(url, register_node=False)
        try:
            data = client.poll()
        except requests.HTTPError as exc:
            print 'error polling %s: %s' % (url, exc)
            continue
        if data['commit'] != commit:
            client.set_commit(commit)
            print '%s: %s (%s)' % (client.name, commit, branch)
        else:
            print '%s: already up-to-date' % client.name


def list_groups(args, config):
    '''
    List available deployment groups.
    '''
    deployment_groups = config.get('deployment_groups', {})
    for name, definition in deployment_groups.items():
        print '%s: branch %s' % (name, definition['branch'])


def current_git_branch():
    '''
    Return the current GIT branch.
    '''
    branches = run('git', 'branch')
    current_branch = [b for b in branches.split('\n') if b.startswith('*')][0]
    return current_branch.split()[1]
