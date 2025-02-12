"""
This file contains the main static application class, CloudHarvestAgent. This class contains the Flask application,
JobQueue instance, and configuration for the agent. The run method is used to start.
"""

from logging import Logger


class CloudHarvestNode:
    """
    A static class which contains the Flask application, JobQueue instance, and configuration for the agent.
    """
    ROLE = 'agent'

    from agent import Api, JobQueue
    from flask import Flask
    api: Api = None
    flask: Flask = None
    config = {}
    job_queue: JobQueue = None

    @staticmethod
    def run(**kwargs):
        """
        This method is used to start the agent. It configures logging, creates the JobQueue, and starts the Flask
        application. It accepts all keyword arguments provided by the configuration file.
        """

        flat_kwargs = flatten_dict_preserve_lists(kwargs)

        # Configure logging
        logger = load_logging(log_destination=flat_kwargs.get('agent.logging.location'),
                              log_level=flat_kwargs.get('agent.logging.level'),
                              quiet=flat_kwargs.get('agent.logging.quiet'))

        logger.info('Agent configuration loaded successfully.')

        logger.info('Agent starting')

        # Create a new API interface which will be used to communicate with the CloudHarvestApi
        CloudHarvestNode.api = CloudHarvestNode.Api(host=flat_kwargs.get('api.host'),
                                                    port=flat_kwargs.get('api.port'),
                                                    token=flat_kwargs.get('api.token'),
                                                    pem=flat_kwargs.get('api.ssl.pem'),
                                                    verify=flat_kwargs.get('api.ssl.verify'))

        # Retrieves the silo configurations used by the agent and TaskChains
        CloudHarvestNode.refresh_silos()

        # Start the heartbeat process
        start_node_heartbeat()

        # Instantiate the JobQueue
        queue = CloudHarvestNode.JobQueue(api=CloudHarvestNode.api,
                                          reporting_interval_seconds=flat_kwargs.get('agent.metrics.reporting_interval_seconds'),
                                          **{k[12:]: v for k, v in flat_kwargs.items() if k.startswith('agent.tasks.')})

        CloudHarvestNode.job_queue = queue

        if flat_kwargs.get('agent.tasks.auto_start', True):
            CloudHarvestNode.job_queue.start()

        ssl_context = (flat_kwargs['agent.connection.pem'], ) if flat_kwargs.get('agent.connection.pem') else ()

        # Start the Flask application
        CloudHarvestNode.flask.run(host=flat_kwargs.get('agent.connection.host', 'localhost'),
                                   port=flat_kwargs.get('agent.connection.port', 8000),
                                   ssl_context=ssl_context)

    @staticmethod
    def refresh_silos():
        """
        Creates silo connections for the agent.
        :return:
        """
        from logging import getLogger
        logger = getLogger('harvest')

        from CloudHarvestCoreTasks.silos import add_silo
        silos = CloudHarvestNode.api.request('get', 'silos/get_all')

        if silos['status_code'] != 200:
            from sys import exit
            logger.critical(f'Could not retrieve silos from the API. {silos["status_code"]}:{silos["reason"]} {silos["url"]}. Exiting.')
            exit(1)

        # Add the silos to make sure they are up to date
        [
            add_silo(name=silo_name, **silo_config)
            for silo_name, silo_config in silos['response']['result'].items()
        ]

        return


def flatten_dict_preserve_lists(d, parent_key='', sep='.') -> dict:
    """
    Flattens a dictionary while preserving lists.

    Arguments
    d (dict): The dictionary to flatten.
    parent_key (str, optional): The parent key. Defaults to ''.
    sep (str, optional): The separator to use. Defaults to '.'.

    Returns
    dict: The flattened dictionary.
    """
    items = []

    for k, v in d.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict_preserve_lists(v, new_key, sep=sep).items())

        else:
            items.append((new_key, v))

    return dict(items)

def start_node_heartbeat(expiration_multiplier: int = 5, heartbeat_check_rate: float = 1):
    """
    Start the heartbeat process on the harvest-nodes silo. This process will update the node status in the Redis
    cache at regular intervals.

    Args:
    expiration_multiplier (int): The multiplier to use when setting the expiration time for the node status in the
                                 Redis cache, rounded up to the nearest integer.
    heartbeat_check_rate (float): The rate at which the heartbeat process should check the node status.

    Example:
        >>> # Start the heartbeat process with a 5x expiration multiplier and a check rate of 1 second. The Agent will be
        >>> # considered offline if it has not updated its status in 5 seconds.
        >>> start_node_heartbeat(expiration_multiplier=5, heartbeat_check_rate=1)
        >>>
        >>> # Start the heartbeat process with an expiration multiplier of 10 and a check rate of 2 seconds. The Agent will
        >>> # be considered offline if it has not updated its status in 10 seconds.
        >>> start_node_heartbeat(expiration_multiplier=10, heartbeat_check_rate=2)

    Returns: The thread object that is running the heartbeat process.
    """

    import platform

    from CloudHarvestCoreTasks.silos import get_silo
    from datetime import datetime, timezone
    from logging import getLogger
    from socket import getfqdn, gethostbyname
    from time import sleep
    from threading import Thread

    logger = getLogger('harvest')

    def _thread():
        start_datetime = datetime.now(tz=timezone.utc)

        # Get the Redis client
        silo = get_silo('harvest-nodes')
        client = silo.connect()     # A StrictRedis instance

        # Get the application metadata
        import json
        with open('./meta.json') as meta_file:
            app_metadata = json.load(meta_file)

            node_name = platform.node()
            node_role = CloudHarvestNode.ROLE

            node_info = {
                "architecture": f'{platform.machine()}',
                "ip": gethostbyname(getfqdn()),
                "heartbeat_seconds": heartbeat_check_rate,
                "name": node_name,
                "os": platform.freedesktop_os_release().get('PRETTY_NAME'),
                "plugins": CloudHarvestNode.config.get('plugins', []),
                "port": CloudHarvestNode.config.get('agent', {}).get('connection', {}).get('port') or 8000,
                "python": platform.python_version(),
                "queue": CloudHarvestNode.job_queue.detailed_status(),
                "role": node_role,
                "start": start_datetime.isoformat(),
                "status": CloudHarvestNode.job_queue.detailed_status(),
                "version": app_metadata.get('version')
            }

        while True:
            # Update the last heartbeat time
            last_datetime = datetime.now(tz=timezone.utc)
            node_info['last'] = last_datetime.isoformat()
            node_info['duration'] = (last_datetime - start_datetime).total_seconds()

            # Update the node status in the Redis cache
            try:
                node_record_identifier = f'{node_role}::{node_name}::{node_info["port"]}'

                client.setex(name=node_record_identifier,
                             value=json.dumps(node_info, default=str),
                             time=int(expiration_multiplier * heartbeat_check_rate))

                logger.debug(f'heartbeat: OK')

            except Exception as e:
                logger.error(f'heartbeat: Could not update silo `harvest-nodes`: {e.args}')

            sleep(heartbeat_check_rate)

    # Start the heartbeat thread
    thread = Thread(target=_thread, daemon=True)
    thread.start()

    return thread

#############################################
# Startup methods                           #
#############################################

def load_configuration_from_file() -> dict:
    from yaml import load, FullLoader

    configuration = {}

    from os.path import abspath, expanduser, exists
    config_paths = (
        abspath(expanduser('./app/harvest.yaml')),
        abspath(expanduser('./harvest.yaml')),
    )

    # Select the first file of the list
    for filename in config_paths:

        if exists(filename):
            with open(filename) as agent_file:
                configuration = load(agent_file, Loader=FullLoader)

            break

    if not configuration:
        raise FileNotFoundError(f'No configuration file found in {config_paths}.')

    # Remove any keys that start with a period. This allows YAML anchors to be used in the configuration file.
    return {
        k:v
        for k, v in configuration.items() or {}.items()
        if not k.startswith('.')
    }

def load_logging(log_destination: str = './app/logs/', log_level: str = 'info', quiet: bool = False, **kwargs) -> Logger:
    """
    This method configures logging for the Agent.

    Arguments
    log_destination (str, optional): The destination directory for the log file. Defaults to './app/logs/'.
    log_level (str, optional): The logging level. Defaults to 'info'.
    quiet (bool, optional): Whether to suppress console output. Defaults to False.
    """
    level = log_level

    from logging import getLogger, Formatter, StreamHandler, DEBUG
    from logging.handlers import RotatingFileHandler

    # startup
    new_logger = getLogger(name='harvest')

    # If the logger exists, remove all of its existing handlers
    if new_logger.hasHandlers():
        [
            new_logger.removeHandler(handler)
            for handler in new_logger.handlers
        ]

    from importlib import import_module
    lm = import_module('logging')
    log_level_attribute = getattr(lm, level.upper())

    # formatting
    log_format = Formatter(fmt='[%(asctime)s][%(levelname)s][%(filename)s] %(message)s')

    # file handler
    from pathlib import Path
    from os.path import abspath, expanduser
    _location = abspath(expanduser(log_destination))

    # make the destination log directory if it does not already exist
    Path(_location).mkdir(parents=True, exist_ok=True)

    # configure the file handler
    from os.path import join
    fh = RotatingFileHandler(join(_location, 'agent.log'), maxBytes=10000000, backupCount=5)
    fh.setFormatter(fmt=log_format)
    fh.setLevel(DEBUG)

    new_logger.addHandler(fh)

    if not quiet:
        # stream handler
        sh = StreamHandler()
        sh.setFormatter(fmt=log_format)
        sh.setLevel(log_level_attribute)
        new_logger.addHandler(sh)

    new_logger.setLevel(log_level_attribute)

    new_logger.debug(f'Logging enabled successfully. Log location: {log_destination}')

    return new_logger
