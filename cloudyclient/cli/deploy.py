'''
``cloudy deploy`` implementation.
'''
import sys
import logging

import requests
import click

from cloudyclient.api import run
from cloudyclient.client import CloudyClient
from cloudyclient.conf import CliConfig, search_up


DEPLOY_CONFIG_FILENAME = '.cloudy.yml'


@click.command()
@click.argument('targets', nargs=-1)
@click.option('--list', '-l', 'list_deployments', is_flag=True,
        help='list deployment groups')
def deploy(targets, list_deployments):
    '''
    Trigger groups of deployments.
    '''
    # Check args
    if not targets and not list_deployments:
        print 'You must specify at least one group name or --list'
        sys.exit(1)

    # Inhibit API logging
    api_logger = logging.getLogger('cloudyclient.api.base')
    api_logger.setLevel(logging.WARNING)

    # Load deploy configuration
    filename = search_up(DEPLOY_CONFIG_FILENAME)
    if filename is None:
        print '"%s" not found in this directory or in parent directories' \
                % DEPLOY_CONFIG_FILENAME
        sys.exit(1)
    config = CliConfig(filename)

    if not list_deployments:
        push_commits(targets, config)
    else:
        list_groups(config)


def push_commits(targets, config):
    # Get deployment groups definitions from configuration
    groups = {}
    groups_commits = {}
    for group_name in targets:
        group_name, _, commit = group_name.partition('@')
        deployment_groups = config.get('deployment_groups', {})
        group = deployment_groups.get(group_name)
        if group is None:
            print 'No such deployment group "%s"' % group_name
            sys.exit(1)
        groups[group_name] = group
        if commit:
            groups_commits[group_name] = commit

    # Retreive the branches to push
    current_git_branch = get_current_git_branch()
    branches = {}
    branches_to_push = set()
    push_tags = False
    for group_name, group in groups.items():
        branch = group.get('branch')
        if branch is None:
            print '"branch" key missing from deployment group "%s"' % \
                    group_name
            sys.exit(1)
        if branch == '__current__':
            branch = current_git_branch
        branches[group_name] = branch
        if group.get('push', False):
            branches_to_push.add(branch)
        if group.get('push_tags', False):
            push_tags = True

    for branch in branches_to_push:
        src_dst = '{0}:{0}'.format(branch)
        print 'git push origin %s' % src_dst
        run('git', 'push', 'origin', src_dst, no_pipes=True)
        print

    if push_tags:
        print 'git push --tags'
        run('git', 'push', '--tags', no_pipes=True)
        print

    for group_name, group in groups.items():
        # Retrieve the commit to deploy
        branch = branches[group_name]
        commit = groups_commits.get(group_name)
        if commit is None:
            commit = run('git', 'rev-parse', branch)
        # Update deployments commits
        poll_urls = group.get('deployments', [])
        if not poll_urls:
            print 'Warning: deployment group "%s" defines no deployments' % \
                    group_name
        for url in poll_urls:
            client = CloudyClient(url, register_node=False)
            try:
                data = client.poll()
            except requests.HTTPError as exc:
                if not getattr(exc, 'printed', False):
                    print 'error polling %s: %s' % (url, exc)
                if getattr(exc, 'final', False):
                    sys.exit(1)
                continue
            if data['commit'] != commit:
                try:
                    client.set_commit(commit)
                except requests.HTTPError as exc:
                    if not getattr(exc, 'printed', False):
                        print 'error updating commit on cloudy: %s' % exc
                    if getattr(exc, 'final', False):
                        sys.exit(1)
                    continue
                print '%s: %s (%s)' % (client.deployment_name, commit, branch)
            else:
                print '%s: already up-to-date' % client.deployment_name


def list_groups(config):
    '''
    List available deployment groups.
    '''
    deployment_groups = config.get('deployment_groups', {})
    for name, definition in sorted(deployment_groups.items()):
        print '%s: branch %s' % (name, definition['branch'])


def get_current_git_branch():
    '''
    Return the current GIT branch.
    '''
    branches = run('git', 'branch')
    current_branch = [b for b in branches.split('\n') if b.startswith('*')][0]
    return current_branch.split()[1]
