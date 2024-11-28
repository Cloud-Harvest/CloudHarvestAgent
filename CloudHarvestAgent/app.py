"""
This file contains the main static application class, CloudHarvestAgent. This class contains the Flask application,
JobQueue instance, and configuration for the agent. The run method is used to start.
"""

from logging import Logger


class CloudHarvestAgent:
    """
    A static class which contains the Flask application, JobQueue instance, and configuration for the agent.
    """
    from agent import Api, JobQueue
    api: Api = None
    app = None
    config = {}
    job_queue: JobQueue = None

    # Maps the flattened YAML configuration to the JobQueue configuration
    # Format: (job_queue_key, configuration_key)
    JOB_QUEUE_CONFIGURATION_MAPPING = (
        ('api_host', 'api.host'),
        ('api_port', 'api.port'),
        ('api_token', 'api.token'),
        ('accepted_chain_priorities', 'agent.tasks.accepted_chain_priorities'),
        ('chain_progress_reporting_interval_seconds', 'agent.tasks.chain_progress_reporting_interval_seconds'),
        ('chain_task_restrictions', 'agent.tasks.chain_task_restrictions'),
        ('chain_timeout_seconds', 'agent.tasks.chain_timeout_seconds'),
        ('queue_check_interval_seconds', 'agent.tasks.queue_check_interval_seconds'),
        ('max_chain_delay_seconds', 'agent.tasks.max_chain_delay_seconds'),
        ('max_running_chains', 'agent.tasks.max_running_chains'),
        ('max_chain_queue_depth', 'agent.tasks.max_chain_queue_depth'),
        ('reporting_interval_seconds', 'agent.metrics.reporting_interval_seconds')
    )

    @staticmethod
    def run(**kwargs):
        """
        This method is used to start the agent. It configures logging, creates the JobQueue, and starts the Flask
        application. It accepts all keyword arguments provided by the configuration file.
        """

        # Configure logging
        logger = load_logging(log_destination=kwargs.get('logging.location'),
                              log_level=kwargs.get('logging.level'),
                              quiet=kwargs.get('logging.quiet'))

        logger.info('Agent configuration loaded successfully.')

        logger.info('Agent starting')

        # Create the JobQueue using the kwargs provided by the configuration
        from flatten_json import flatten_preserve_lists
        flat_kwargs = flatten_preserve_lists(kwargs, separator='.')

        # Create a new API interface which will be used to communicate with the CloudHarvestApi
        CloudHarvestAgent.api = CloudHarvestAgent.Api(host=kwargs['api.host'],
                                                      port=kwargs['api.port'],
                                                      token=kwargs['api.token'])

        # Retrieves the silo configurations and implements them for the TaskChains
        CloudHarvestAgent.refresh_silos()

        # Map the flattened configuration to the JobQueue configuration
        job_queue_kwargs = {
            job_queue_key: flat_kwargs[configuration_key]
            for job_queue_key, configuration_key in CloudHarvestAgent.JOB_QUEUE_CONFIGURATION_MAPPING
        }

        # Instantiate the JobQueue
        CloudHarvestAgent.job_queue = CloudHarvestAgent.JobQueue(api=CloudHarvestAgent.api, **job_queue_kwargs)
        CloudHarvestAgent.job_queue.start()

        logger.info(f'Agent startup complete. Will serve requests on {CloudHarvestAgent.app.url_map}.')

        # Start the Flask application
        CloudHarvestAgent.app.run(**kwargs)

    @staticmethod
    def refresh_silos():
        """
        Creates silo connections for the agent.
        :return:
        """

        from CloudHarvestCoreTasks.silos import add_silo
        silos = CloudHarvestAgent.api.request('get', 'silos/get')['response']

        # Update the silos to make sure they are up to date
        [
            add_silo(**silo)
            for silo in silos
        ]


#############################################
# Startup methods                           #
#############################################

def load_logging(log_destination: str = './app/logs/', log_level: str = 'info', quiet: bool = False) -> Logger:
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

    from importlib import import_module
    lm = import_module('logging')
    log_level_attribute = getattr(lm, level.upper())

    # clear existing log handlers anytime this library is called
    [new_logger.removeHandler(handler) for handler in new_logger.handlers]

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

    if quiet is False:
        # stream handler
        sh = StreamHandler()
        sh.setFormatter(fmt=log_format)
        sh.setLevel(log_level_attribute)
        new_logger.addHandler(sh)

    new_logger.setLevel(log_level_attribute)

    new_logger.debug('logging: enabled')

    return new_logger
