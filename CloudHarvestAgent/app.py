from logging import getLogger

logger = getLogger('harvest')


class CloudHarvestAgent:
    from .agent import Api, JobQueue
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
        from flatten_json import flatten_preserve_lists

        logger.info('Agent starting')

        # Create the JobQueue using the kwargs provided by the configuration
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

        logger.info(f'Agent startup complete. Will serve requests on {CloudHarvestAgent.app.url_map}')

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
