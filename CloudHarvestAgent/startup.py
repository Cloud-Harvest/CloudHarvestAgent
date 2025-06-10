from CloudHarvestCoreTasks.dataset import WalkableDict
from CloudHarvestCoreTasks.environment import Environment

from logging import Logger


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


def start_node_heartbeat(config: WalkableDict):
    """
    Start the heartbeat process on the harvest-nodes silo. This process will update the node status in the Redis
    cache at regular intervals.

    Args:
    config (WalkableDict): The configuration for the node heartbeat process.

    Example:
        >>> # Start the heartbeat process with a 5x expiration multiplier and a check rate of 1 second. The API will be
        >>> # considered offline if it has not updated its status in 5 seconds.
        >>> start_node_heartbeat(expiration_multiplier=5, heartbeat_check_rate=1)
        >>>
        >>> # Start the heartbeat process with an expiration multiplier of 10 and a check rate of 2 seconds. The API will
        >>> # be considered offline if it has not updated its status in 10 seconds.
        >>> start_node_heartbeat(expiration_multiplier=10, heartbeat_check_rate=2)

    Returns: The thread object that is running the heartbeat process.
    """

    heartbeat_check_rate = config.walk('agent.heartbeat.check_rate') or 1
    expiration_multiplier = config.walk('agent.heartbeat.expiration_multiplier') or 5

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
        node_silo = get_silo('harvest-nodes')
        node_client = node_silo.connect()     # A StrictRedis instance

        template_silo = get_silo('harvest-templates')
        template_client = template_silo.connect()  # A StrictRedis instance

        # Get the application metadata
        import json
        with open('./meta.json') as meta_file:
            app_metadata = json.load(meta_file)

        from CloudHarvestCorePluginManager import Registry
        node_name = platform.node()
        node_role = 'agent'

        node_info = {
            "accounts": sorted([
                f'{p}:{account}'
                for p in config.get('platforms', {}).keys() or []
                for account in config['platforms'][p].get('accounts') or []
            ]),
            "architecture": f'{platform.machine()}',
            "available_chains": sorted(Registry.find(category='chain', result_key='name', limit=None)),
            "available_tasks": sorted(Registry.find(category='task', result_key='name', limit=None)),
            "ip": gethostbyname(getfqdn()),
            "heartbeat_seconds": heartbeat_check_rate,
            "name": node_name,
            "os": platform.freedesktop_os_release().get('PRETTY_NAME'),
            "plugins": config.walk('plugins', []),
            "pid": config.walk('agent.pid'),
            "port": config.walk('agent.connection.port') or 8500,
            "python": platform.python_version(),
            "queue": Environment.get('queue_object').detailed_status(),
            "role": node_role,
            "start": start_datetime.isoformat(),
            "status": Environment.get('queue_object').detailed_status(),
            "version": app_metadata.get('version')
        }

        node_record_identifier = config.walk('agent.name')

        def format_for_redis(dictionary: dict) -> dict:
            """
            Format the dictionary for Redis HSET. This method converts all non-string, non-integer, and non-float
            values to JSON strings. This is necessary because Redis supports a limited array of data types.
            Args:
                dictionary (dict): The dictionary to format.

            Returns:
                dict: The formatted dictionary.
            """

            # Format the records
            for key, value in dictionary.items():
                if not isinstance(value, (str, int, float)):
                    dictionary[key] = json.dumps(value, default=str)

            return dictionary

        # Record the information to Redis
        node_client.hset(node_record_identifier, mapping=format_for_redis(node_info))

        stored_templates = None

        while True:
            templates = Registry.find(category='template_*', result_key='*', limit=None)

            # Update the last heartbeat time
            last_datetime = datetime.now(tz=timezone.utc)
            node_info |= {
                "available_templates": sorted([
                    f'{result["category"]}/{result["name"]}'
                    for result in templates
                ]),
                'last': last_datetime.isoformat(),
                'duration': (last_datetime - start_datetime).total_seconds()
            }

            # Update the node status in the Redis cache
            try:
                expiration = int(expiration_multiplier * heartbeat_check_rate)

                # Record the information to Redis
                node_client.hset(node_record_identifier, mapping=format_for_redis(node_info))

                # Set the expiration time for the node record
                node_client.expire(node_record_identifier, expiration)

                logger.debug(f'heartbeat: OK')

                # Update the templates but only if they have changed
                if stored_templates != templates:
                    stored_templates = templates

                    # Create a record of the templates in Redis
                    for template in templates:
                        template_identifier = f'{template["category"].split('_', 1)[1]}/{template["name"]}'
                        task_class = list(template.get('cls', {}).keys())[0] if template.get('cls') else None
                        if not task_class:
                            continue

                        from copy import deepcopy
                        from json import loads
                        task_config = deepcopy(template['cls'][task_class])
                        task_config['class'] = task_class

                        template_client.hset(
                            name=template_identifier,
                            mapping=format_for_redis(task_config)
                        )

                        template_client.expire(template_identifier, expiration)

                else:
                    # If the templates have not changed, just update their expiration time
                    for template in templates:
                        template_identifier = f'{template["category"].split("_", 1)[1]}/{template["name"]}'
                        template_client.expire(template_identifier, expiration)

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
    This method configures logging for the api.

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
    log_format = Formatter(fmt='[%(asctime)s][%(process)d][%(levelname)s][%(filename)s] %(message)s')

    # file handler
    from pathlib import Path
    from os.path import abspath, expanduser
    _location = abspath(expanduser(log_destination))

    # make the destination log directory if it does not already exist
    Path(_location).mkdir(parents=True, exist_ok=True)

    # configure the file handler
    from os.path import join
    fh = RotatingFileHandler(join(_location, 'api.log'), maxBytes=10000000, backupCount=5)
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


def refresh_silos():
    """
    Creates silo connections for the agent.
    :return:
    """
    from logging import getLogger
    logger = getLogger('harvest')

    from CloudHarvestCoreTasks.silos import add_silo
    silos = Environment.get('api_object').request('get', 'silos/get_all')

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