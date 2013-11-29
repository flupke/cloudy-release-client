import argparse
import logging
import time
import json
import traceback

from cloudyclient import log
from cloudyclient.client import CloudyClient
from cloudyclient.api import dry_run, run, get_global
from cloudyclient.state import (get_state_directory, get_data_filename,
        load_data)
from cloudyclient.conf import settings
from cloudyclient.conf.local import load_conf
from cloudyclient.checkout import get_implementation


logger = logging.getLogger(__name__)


def main():
    # Parse command line
    parser = argparse.ArgumentParser(description='cloudy-release client')
    parser.add_argument('--run-once', '-1', action='store_true', 
            help='update all deployments and exit; the default is to poll '
            'deployments forever')
    parser.add_argument('--dry-run', '-d', action='store_true',
            help='do not modify anything, just log commands that should be '
            'executed')
    args = parser.parse_args()

    # Load configuration
    load_conf()

    # Setup logging
    log.setup()

    # Execute deployments
    while True:
        if args.dry_run:
            with dry_run():
                poll_deployments()
        else:
            poll_deployments()
        if args.run_once:
            break
        time.sleep(settings.POLL_INTERVAL)


def poll_deployments():
    '''
    Poll all deployments and deploy them if necessary.
    '''
    dry_run = get_global('dry_run', False)
    client = None
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
            if depl_hash == prev_depl_hash:
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
                success = deploy(data)
                output = mem_handler.value()
                if success:
                    client.success(output)
                else:
                    client.error(output)
        except:
            # Something bad happened, try to log error to the server
            try:
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


def deploy(data):
    '''
    Do a single deployment, using the *data* dict that was retrieved from the
    server.

    Returns a boolean indicating if the the deployment was successful.
    '''
    dry_run = get_global('dry_run', False)
    base_dir = data['base_dir']
    project_name = data['project_name']
    repository_type = data['repository_type']
    # Checkout code
    try:
        checkout_class = get_implementation(repository_type)
    except KeyError:
        logger.error('unknown repository type "%s"', repository_type)
        return False
    checkout = checkout_class()
    checkout.get_commit(base_dir, project_name, data['repository_url'],
            data['commit'])
    # Write deployment data in the state directory
    if not dry_run:
        data_filename = get_data_filename(base_dir, project_name)
        with open(data_filename, 'w') as fp:
            json.dump(data, fp, indent=4)
    return True
