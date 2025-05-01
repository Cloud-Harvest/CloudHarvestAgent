"""
Entrypoint for the CloudHarvestAgent
"""
from CloudHarvestAgent.api import Api
from CloudHarvestAgent.jobs import JobQueue
from CloudHarvestAgent.startup import (
    load_configuration_from_file,
    load_logging,
    refresh_silos,
    start_node_heartbeat
)
from CloudHarvestCorePluginManager import Registry, register_all
from CloudHarvestCorePluginManager.plugins import generate_plugins_file, install_plugins
from CloudHarvestCoreTasks.dataset import WalkableDict
from CloudHarvestCoreTasks.environment import Environment
from argparse import ArgumentParser, Namespace
from flask import Flask

# Imports objects which need to be registered by the CloudHarvestCorePluginManager
from CloudHarvestAgent.__register__ import *

# The flask server object
app = Flask('CloudHarvestAgent')


if __name__ == '__main__':
    parser = ArgumentParser(description='CloudHarvestAgent')
    debug_group = parser.add_argument_group('DEBUG OPTIONS', description='Options when running the application in '
                                                                         'debug mode. None of the options presented here '
                                                                         'are required if the application is running using '
                                                                         'a WSGI server, such as gunicorn.')
    debug_group.add_argument('--host', type=str, default='127.0.0.1', help='Host address')
    debug_group.add_argument('--port', type=int, default=8500, help='Port number')
    debug_group.add_argument('--pemfile', type=str, default='./app/harvest-self-signed.pem', help='Use PEM file for SSL')
    debug_group.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

else:
    # If the script is not run as the main module, collect the variables from the environment
    from os import environ
    args = Namespace(host=environ.get('CLOUDHARVESTAGENT_HOST'),
                     port=int(environ.get('CLOUDHARVESTAGENT_PORT')),
                     pemfile=environ.get('CLOUDHARVESTAGENT_PEMFILE'),
                     debug=False)

# Load the configuration
config = WalkableDict(**load_configuration_from_file())
config['agent']['connection'] = vars(args)

# Makes the configuration available throughout the app
Environment.merge(config)

# Install plugins
generate_plugins_file(config.walk('plugins') or {})
install_plugins(quiet=args.debug or config.walk('agent.logging.quiet'))

# Find all plugins and register their objects and templates
register_all()

# Register the blueprints from this app and all plugins
with app.app_context():
    [
        app.register_blueprint(api_blueprint)
        for api_blueprint in Registry.find(result_key='instances',
                                           category='blueprint',
                                           name='agent')
        if api_blueprint is not None
    ]


# Configure logging
logger = load_logging(log_destination=config.walk('agent.logging.location'),
                      log_level=config.walk('agent.logging.level'),
                      quiet=config.walk('agent.logging.quiet'))

logger.info('Agent configuration loaded successfully.')

# Create a new API interface which will be used to communicate with the CloudHarvestApi
api = Api(host=config.walk('api.host'),
          port=config.walk('api.port'),
          token=config.walk('api.token'),
          pem=config.walk('api.ssl.pem'),
          verify=config.walk('api.ssl.verify'))

# Instantiate the JobQueue
queue = JobQueue(api=api,
                 reporting_interval_seconds=config.walk('agent.metrics.reporting_interval_seconds'),
                 **config.walk('agent.tasks', {}))

Environment.add(name='api_object', value=api)
Environment.add(name='queue_object', value=queue)

# Retrieves the list of silos from the API
refresh_silos()

# Start the node heartbeat
start_node_heartbeat(config)

logger.debug(app.url_map)

if config.walk('agent.tasks.auto_start', True):
    queue.start()

logger.info('Agent node started.')

if args.debug:
    import ssl

    # Create SSL context using the PEM file
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(args.pemfile)

    # Start the Flask application
    app.run(host=args.host,port=args.port, ssl_context=ssl_context)
