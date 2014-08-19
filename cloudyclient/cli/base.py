import os
import argparse
import logging

from cloudyclient import log
from cloudyclient.conf.local import load_conf
from cloudyclient.cli.poll import poll
from cloudyclient.cli.deploy import deploy


logger = logging.getLogger(__name__)


def main():
    # Load configuration
    load_conf()

    # Create main parser
    parser = argparse.ArgumentParser(description='A cloudy-release client.')
    parser.add_argument('--log-level', '-l', default='info')
    subparsers = parser.add_subparsers(help='sub-command help')

    # cloudy poll ...
    poll_parser = subparsers.add_parser('poll',
            description='Poll for deployments and execute new ones.')
    poll_parser.add_argument('--run-once', '-1', action='store_true',
            help='update all deployments and exit; the default is to poll '
            'deployments forever')
    poll_parser.add_argument('--dry-run', '-d', action='store_true',
            help='do not modify anything, just log commands that should be '
            'executed')
    poll_parser.add_argument('--force', '-f', action='store_true',
            help='always poll regardless of local state')
    poll_parser.add_argument('--first-round-lock', help='this file is created '
            'on startup, and removed once all the deployments have been '
            'polled once')
    poll_parser.set_defaults(func=poll)

    # cloudy deploy ...
    deploy_parser = subparsers.add_parser('deploy',
            description='Trigger groups of deployments.')
    deploy_parser.add_argument('group', nargs='*',
            help='deployments group name, or group@commit')
    deploy_parser.add_argument('-l', '--list', action='store_true',
            help='list deployment groups')
    deploy_parser.set_defaults(func=deploy)

    # Parse command line
    args = parser.parse_args()

    # Setup logging
    os.environ['CLOUDY_LOG_LEVEL'] = args.log_level
    log.setup()

    # Run sub-command function
    args.func(args)
