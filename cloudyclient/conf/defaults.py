import socket

# The list of deployment poll URLs from which the client gets its
# configurations
POLL_URLS = []

# Number of times VCS commands are retried before failing
VCS_RETRIES = 10

# Deployments poll interval in seconds
POLL_INTERVAL = 3

# Client requests settings
REQUESTS_TIMEOUT = 10
REQUESTS_RETRIES = 3
REQUESTS_POOL_SIZE = 30

# The name used to identify this node in the cloudy-release server
NODE_NAME = socket.getfqdn()

# Default format for all loggers
LOGS_FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
