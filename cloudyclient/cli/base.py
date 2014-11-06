import os
import logging

import click

from cloudyclient import log
from cloudyclient.conf import load_conf
from cloudyclient.cli.poll import poll
from cloudyclient.cli.deploy import deploy


logger = logging.getLogger(__name__)


@click.group()
@click.option('--log-level', '-l', default='info')
def main(log_level):
    # Load configuration
    load_conf()

    # Setup logging
    os.environ['CLOUDY_LOG_LEVEL'] = log_level
    log.setup()


main.add_command(poll)
main.add_command(deploy)
