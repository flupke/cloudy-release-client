'''
``cloudy poll`` implementation.
'''
import os
import time
import logging
import os.path as op
import traceback
import json
import subprocess

from requests.exceptions import Timeout
import click

from cloudyclient import log
from cloudyclient.api import dry_run as dry_run_ctx, get_global, run
from cloudyclient.conf import settings
from cloudyclient.client import CloudyClient
from cloudyclient.state import (get_state_directory, get_data_filename,
        load_data)
from cloudyclient.checkout import get_implementation
from cloudyclient.deploy import DeploymentScript


logger = logging.getLogger(__name__)


@click.command()
@click.option('--run-once/--no-run-once', default=False,
        help='update all deployments and exit; the default is to poll '
        'deployments forever')
@click.option('--dry-run/--no-dry-run', default=False,
        help='do not modify anything, just log commands that should be '
        'executed')
@click.option('--force/--no-force', default=False,
        help='always deploy regardless of local state')
@click.option('--first-round-lock', metavar='FILE',
        help='this file is created on startup, and removed once all the '
        'deployments have been polled once')
def poll(run_once, dry_run, force, first_round_lock):
    '''
    Poll for deployments and execute new ones.
    '''
    # Create first round lock
    if first_round_lock:
        try:
            open(first_round_lock, 'w').close()
        except:
            logger.error('failed to create first round lock', exc_info=True)
            remove_lock = False
        else:
            remove_lock = True
    else:
        remove_lock = False

    # Poll deployments
    while True:
        if dry_run:
            with dry_run_ctx():
                poll_deployments(force)
        else:
            try:
                poll_deployments(force)
            except Timeout:
                remove_lock = False
        if remove_lock:
            try:
                os.unlink(first_round_lock)
            except:
                logger.error('failed to remove first round lock',
                        exc_info=True)
            remove_lock = False
        if run_once:
            break
        time.sleep(settings.poll_interval)


def poll_deployments(force):
    '''
    Poll all deployments and execute the ones that need to.
    '''
    dry_run = get_global('dry_run', False)
    client = None
    base_dir = None
    project_name = None
    mem_handler = None
    handlers = []
    for url in settings.poll_urls:
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
            if not force and depl_hash == prev_depl_hash:
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
    checkout = checkout_class(base_dir, project_name, data['repository_url'],
            data['commit'])
    checkout_dir = checkout.get_commit()
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
    # Finalize commit
    checkout.finalize_commit()
    return True
