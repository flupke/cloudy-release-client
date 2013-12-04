import sys
import os
import os.path as op
import argparse
import logging
import time
import json
import traceback
import subprocess

import requests

from cloudyclient import log
from cloudyclient.client import CloudyClient
from cloudyclient.api import dry_run, run, get_global
from cloudyclient.state import (get_state_directory, get_data_filename,
        load_data)
from cloudyclient.conf import settings
from cloudyclient.conf.local import load_conf
from cloudyclient.checkout import get_implementation
from cloudyclient.deploy import DeploymentScript


logger = logging.getLogger(__name__)


def main():
    # Load configuration
    load_conf()

    # Setup logging
    log.setup()    

    # Parse command line
    parser = argparse.ArgumentParser(description='cloudy-release client')
    subparsers = parser.add_subparsers(help='sub-command help')

    # cloudy deploy ...
    deploy_parser = subparsers.add_parser('deploy', 
            help='execute deployments')
    deploy_parser.add_argument('--run-once', '-1', action='store_true', 
            help='update all deployments and exit; the default is to poll '
            'deployments forever')
    deploy_parser.add_argument('--dry-run', '-d', action='store_true',
            help='do not modify anything, just log commands that should be '
            'executed')
    deploy_parser.add_argument('--force', '-f', action='store_true',
            help='always deploy regardless of local state')
    deploy_parser.set_defaults(func=deploy)

    # cloudy commit ...
    commit_parser = subparsers.add_parser('commit', help='get or retrieve '
            'current commit of a deployment')
    commit_parser.add_argument('deployment', 
            help='deployment name (you can pass a part of the name)')
    commit_parser.add_argument('commit', nargs='?', 
            help='if given, set the deployment\'s commit to this commit')
    commit_parser.set_defaults(func=commit)
    
    # Run subcommand function
    args = parser.parse_args()
    args.func(args)


def deploy(args):
    '''
    Execute deployments.
    '''
    while True:
        if args.dry_run:
            with dry_run():
                poll_deployments(args)
        else:
            poll_deployments(args)
        if args.run_once:
            break
        time.sleep(settings.POLL_INTERVAL)


def commit(args):
    '''
    Get or set a deployment's commit.
    '''
    # Retrieve the deployment by name
    matches = []
    all_deployments = []
    for url in settings.DEPLOYMENTS:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            full_name = '{project_name}/{deployment_name}'.format(**data)
            all_deployments.append(full_name)
            if args.deployment in full_name:
                matches.append((full_name, data))

    # Error out if we do not have exactly one match
    if len(matches) == 0:
        print 'no deployment found matching "%s"; choose one of:\n\n%s' % (
                args.deployment, '\n'.join(all_deployments))
        sys.exit(1)
    elif len(matches) != 1:
        print 'more than one deployment matches "%s":\n\n%s' % (
                args.deployment, '\n'.join(m[0] for m in matches))
        sys.exit(1)

    # Found deployment, get or set commit
    full_name, data = matches[0]
    if args.commit is not None:
        resp = requests.post(data['commit_url'], data={'commit': args.commit})
        try:
            resp.raise_for_status()
        except Exception as exc:
            print 'failed setting %s commit: %s' % (full_name, exc)
            sys.exit(1)
        print 'successfully changed %s commit to %s' % (full_name, args.commit)
    else:
        resp = requests.get(data['commit_url'])
        print '%s: %s' % (full_name, resp.json())


def poll_deployments(args):
    '''
    Poll all deployments and execute the ones that need to.
    '''
    dry_run = get_global('dry_run', False)
    client = None
    base_dir = None
    project_name = None 
    mem_handler = None
    handlers = []
    for url in settings.DEPLOYMENTS:
        try:
            logger.debug('polling %s', url)
            # Retrieve deployment data from server
            client = CloudyClient(url, dry_run=dry_run)
            data = client.poll()
            base_dir = data['base_dir']
            project_name = data['project_name']
            # Get previous deployment hash
            previous_data = load_data(base_dir, project_name)
            depl_hash = data['deployment_hash']
            prev_depl_hash = previous_data.get('deployment_hash')
            if not args.force and depl_hash == prev_depl_hash:
                # Nothing new to deploy
                logger.debug('already up-to-date')
                continue
            # Notify server that the deployment started
            client.pending()
            # Create state directory (this needs to be done before creating
            # the deployment's file logging handler)
            state_dir = get_state_directory(base_dir, project_name)
            run('mkdir', '-p', state_dir)
            # Create temporary logging handlers to catch messages in the
            # deployment state dir and in memory
            file_handler, mem_handler = log.get_deployment_handlers(
                    base_dir, project_name)
            if dry_run:
                handlers = [mem_handler]
            else:
                handlers = [file_handler, mem_handler]
            # Execute deployment
            with log.add_hanlers(*handlers):
                success = execute_deployment(data)
                output = mem_handler.value()
                if success:
                    client.success(output)
                else:
                    client.error(output)
        except:
            # Something bad happened
            try:
                # Remove data file because we want to redo the deployment in
                # the next run
                if (client is not None and base_dir is not None and 
                        project_name is not None):
                    data_path = get_data_filename(base_dir, project_name)
                    if op.exists(data_path):
                        os.unlink(data_path)
                # Try to log error to the server
                message = 'unexpected error while deploying from "%s"'
                with log.add_hanlers(*handlers):
                    logger.error(message, url, exc_info=True)
                if client is not None:
                    if mem_handler is not None:
                        output = mem_handler.value()
                    else:
                        output = '%s:\n%s' % (message % url, 
                                traceback.format_exc())
                    client.error(output)
            except:
                # Server is probably unreachable, move on
                with log.add_hanlers(*handlers):
                    logger.error('cannot log error to server', exc_info=True)
        finally:
            client = None
            mem_handler = None
            handlers = []
            base_dir = None
            project_name = None


def execute_deployment(data):
    '''
    Do a single deployment, using the *data* dict that was retrieved from the
    server.

    Returns a boolean indicating if the the deployment was successful.
    '''
    dry_run = get_global('dry_run', False)
    base_dir = data['base_dir']
    project_name = data['project_name']
    repository_type = data['repository_type']
    deployment_script_type = data['deployment_script_type']
    deployment_script = data['deployment_script']
    # Checkout code
    try:
        checkout_class = get_implementation(repository_type)
    except KeyError:
        logger.error('unknown repository type "%s"', repository_type)
        return False
    checkout = checkout_class()
    checkout_dir = checkout.get_commit(base_dir, project_name, 
            data['repository_url'], data['commit'])
    # Write deployment data in the state directory
    if not dry_run:
        data_filename = get_data_filename(base_dir, project_name)
        with open(data_filename, 'w') as fp:
            json.dump(data, fp, indent=4)
    # Execute deployment script
    script = DeploymentScript(deployment_script_type, deployment_script)
    try:
        script.run(checkout_dir)
    except subprocess.CalledProcessError:
        logger.error('deployment script failed')
        return False
    except:
        logger.error('deployment script failed', exc_info=True)
        return False
    return True
