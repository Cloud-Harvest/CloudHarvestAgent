from logging import getLogger
from redis import StrictRedis
from threading import Thread
from typing import Dict, List, Tuple
from CloudHarvestCoreTasks.chains import BaseTaskChain
from CloudHarvestCoreTasks.tasks import TaskStatusCodes

logger = getLogger('harvest')


class JobQueue:
    """
    The JobQueue class is responsible for checking the Redis queue for new tasks and adding them to the queue. It also
    reports the status of any running task chains to the harvest-agents silo.
    """
    from CloudHarvestAgent.api import Api

    def __init__(self,
                 api: Api,
                 accepted_chain_priorities: List[int],
                 chain_progress_reporting_interval_seconds: int,
                 chain_task_restrictions: List[str],
                 chain_timeout_seconds: int,
                 queue_check_interval_seconds: int,
                 max_chains: int,
                 reporting_interval_seconds: int,
                 *args, **kwargs):

        """
        The JobQueue class is responsible for checking the Redis queue for new tasks and adding them to the queue. It also
        manages the queue and provides methods to interact with it.

        Parameters
        api_host (str): The host of the API.
        api_port (int): The port of the API.
        api_token (str): The token to authenticate with the API.
        accepted_chain_priorities (List[int]): A list of accepted chain priorities.
        chain_progress_reporting_interval_seconds (int): The interval in seconds for reporting chain progress.
        chain_task_restrictions (List[str]): A list of task restrictions for the chains.
        chain_timeout_seconds (int): The timeout in seconds for each chain.
        queue_check_interval_seconds (int): The interval in seconds for checking the queue.
        max_running_chains (int): The maximum number of running chains.
        reporting_interval_seconds (int): The interval in seconds for reporting.

        Additional Parameters:
        The following are provided but not used to avoid errors when passing the configuration file to the JobQueue.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
        """

        super().__init__()

        # Api configuration
        self.api = api

        # Queue configuration
        self.accepted_chain_priorities = accepted_chain_priorities
        self.chain_progress_reporting_interval_seconds = chain_progress_reporting_interval_seconds
        self.chain_task_restrictions = chain_task_restrictions
        self.chain_timeout_seconds = chain_timeout_seconds
        self.queue_check_interval_seconds = queue_check_interval_seconds
        self.max_chains = max_chains
        self.reporting_interval_seconds = reporting_interval_seconds

        # Internal threads
        self._reporting_thread = None
        self._check_queue_thread = None

        # TaskChain Pool Management
        self.task_chains: Dict[str, BaseTaskChain] = {}
        self.task_chain_threads: Dict[str, Thread] = {}

        # Programmatic attributes
        from datetime import datetime, timezone
        self.start_time = datetime.now(tz=timezone.utc)
        self.status = TaskStatusCodes.initialized
        self.stop_time = None

    def _thread_check_queue(self):
        """
        A thread that checks the Redis queue for new tasks and adds them to the JobQueue.
        :return: None
        """

        from CloudHarvestCoreTasks.silos import get_silo
        from time import sleep

        silo = get_silo('harvest-task-queue')
        client: StrictRedis = silo.connect()

        # If there is room in the JobQueue, and it is running, continue to check the Redis queue
        while not self.is_queue_full and self.status == JobQueueStatusCodes.running:

            # First cleanup and finished task chains to make room for new ones
            self.clean_queue()

            # Retrieve the oldest task from the queue
            oldest_task = get_oldest_task_from_queue(client, self.accepted_chain_priorities)

            if oldest_task:
                task_chain_id, task_chain_template = oldest_task

                try:
                    # Instantiate the task chain from the template, add it to the job queue, and start it
                    self.add_task_chain_from_dict(task_chain_id=task_chain_id, task_chain_model=task_chain_template)

                except Exception as ex:
                    logger.error(f'Error while adding task chain {task_chain_id} to the JobQueue: {ex.args}')

                    from datetime import datetime, timezone
                    from json import dumps

                    now = datetime.now(tz=timezone.utc)

                    tasks_silo_client = get_silo('harvest-tasks').connect()
                    error_metadata = {
                        "id": task_chain_id,
                        "end": now,
                        "message": f"Error when creating the TaskChain: {ex.args}",
                        "status": "error",
                        "updated": now
                    }

                    tasks_silo_client.setex(name=task_chain_id, value=dumps(error_metadata, default=str), time=3600)

            # Sleep for the queue check interval
            sleep(self.queue_check_interval_seconds)

    @property
    def is_queue_full(self) -> bool:
        """
        Returns a boolean indicating whether the queue is full.
        :return:
        """
        return len(self.task_chain_threads.keys()) >= self.max_chains

    def _thread_reporting(self):
        """
        A thread that reports the progress of the task chains to the API.
        :return:
        """
        from datetime import datetime, timezone
        from json import dumps
        from time import sleep

        from CloudHarvestCoreTasks.silos import get_silo

        silo = get_silo('harvest-tasks')
        client = silo.connect()

        while True:
            try:

                for task_chain_id, task_chain in list(self.task_chains.items()):
                    task_chain_metadata = {
                                    'id': task_chain.id,
                                    'status': str(task_chain.status),
                                    'start': task_chain.start,
                                    'end': task_chain.end,
                                    'updated': datetime.now(tz=timezone.utc),
                                } | task_chain.detailed_progress()

                    # Report the progress of the task chain to the API
                    client.setex(name=task_chain_id, value=dumps(task_chain_metadata), time=3600)

                    # Escape the loop if the task chain is complete or terminating
                    if self.status in [TaskStatusCodes.complete, TaskStatusCodes.terminating]:
                        break

            except Exception as e:
                logger.error(f'Error while reporting chain progress: {e.args}')

            else:
                logger.debug('progress: OK')

            finally:
                sleep(self.reporting_interval_seconds)

    def add_task_chain(self, task_chain_id: str, task_chain: BaseTaskChain) -> 'JobQueue':
        """
        Adds a TaskChain to the JobQueue and starts it.

        Arguments
        task_chain_id (str): The ID of the TaskChain to add to the JobQueue.
        task_chain (BaseTaskChain): The TaskChain to add to the JobQueue.

        Returns
        self
        """

        # Determine if the task chain is already in the queue
        # We use this technique to prevent clobbering an existing task chain with the same ID
        existing_task_chain = self.task_chains.get(task_chain_id) or task_chain

        if existing_task_chain:
            logger.warning(f'Task chain with ID {task_chain_id} already exists. Skipping.')
            return self

        # Retrieve or create a thread for the task chain
        thread = self.task_chain_threads.get(task_chain_id) or Thread(target=task_chain.run, daemon=True)

        # Add the task chain to the JobQueue
        self.task_chain_threads[task_chain_id] = thread

        # Start the task chain
        thread.start()

        logger.debug(f'{task_chain_id}: Added to the queue.')

        return self

    def add_task_chain_from_dict(self, task_chain_id: str, task_chain_model: dict) -> BaseTaskChain:
        from CloudHarvestCorePluginManager import Registry
        from copy import deepcopy
        # We deepcopy the template so that the copy in the Registry is not modified
        task_structure = deepcopy(Registry.find(result_key='cls', name=task_chain_model['name'], category=task_chain_model['category']))

        if task_structure:
            task_structure = task_structure[0]

        else:
            raise ValueError(f'{task_chain_id}: Task model `{task_chain_model["category"]}/{task_chain_model["name"]}` not found in the Registry.')

        # Create a task chain from the template from the dictionary
        from CloudHarvestCoreTasks.factories import task_chain_from_dict
        task_chain = task_chain_from_dict(template=task_structure, **task_chain_model['config'])

        # Override the BaseTaskChain's id with the task's id
        task_chain.id = task_chain_id

        # Set the TaskChain's result silo
        task_chain.results_silo = 'harvest-task-results'

        # Add this task chain to the JobQueue
        self.add_task_chain(task_chain_id=task_chain_id, task_chain=task_chain)

        return task_chain

    def clean_queue(self) -> 'JobQueue':
        """
        Removes completed and errant TaskChains from the JobQueue
        :return: self
        """

        removed = []
        for task_chain_id, thread in self.task_chain_threads.items():
            task_chain = self.task_chains.get(task_chain_id)

            if not task_chain:
                removed.append(task_chain_id)
                continue

            # Remove the task chain from the queue if its thread is not alive and its status is complete or error
            if not thread.is_alive() and self.task_chains[task_chain_id].status in (TaskStatusCodes.complete, TaskStatusCodes.error):
                self.task_chain_threads.pop(task_chain_id, None)
                self.task_chains.pop(task_chain_id, None)
                removed.append(task_chain_id)

        if removed:
            for task_chain_reference in (self.task_chains, self.task_chain_threads):
                for task_chain_id in removed:
                    task_chain_reference.pop(task_chain_id, None)

            logger.debug(f'Removed {len(removed)} task chains: {removed}')

        return self

    def detailed_status(self) -> dict:
        """
        Returns detailed status information about the JobQueue.
        :return:
        """

        from CloudHarvestCoreTasks.tasks import TaskStatusCodes

        result = {
            'chain_status': {
                str(status_code): sum(1 for task in self.task_chains.values() if task.status == status_code)
                for status_code in TaskStatusCodes.get_codes()
            },
            'duration': self.duration,
            'max_chains': self.max_chains,
            'start_time': self.start_time,
            'status': self.status,
            'stop_time': self.stop_time,
            'total_chains_in_queue': len(self.task_chain_threads)
        }

        return result

    @property
    def duration(self) -> float:
        """
        Returns the duration of the JobQueue in seconds.
        :return:
        """
        from datetime import datetime, timezone

        if self.stop_time:
            result = (self.stop_time - self.start_time).total_seconds()

        else:
            result = (datetime.now(tz=timezone.utc) - self.start_time).total_seconds()

        return result

    def start(self) -> dict:
        """
        Starts the job queue process.
        :return: A dictionary containing the result and message.
        """

        logger.info('Starting the JobQueue.')

        # Set the queue status to 'running'
        self.status = JobQueueStatusCodes.running

        # Reset the stop time
        self.stop_time = None

        try:

            # Start the reporting and queue check threads
            from threading import Thread
            self._reporting_thread = Thread(target=self._thread_reporting, daemon=True)
            self._check_queue_thread = Thread(target=self._thread_check_queue, daemon=True)

            self._reporting_thread.start()
            self._check_queue_thread.start()

        except Exception as ex:
            message = f'Error while starting the JobQueue: {ex.args}'
            logger.error(message)
            self.status = JobQueueStatusCodes.error

        else:
            message = 'OK'

        return {
            'success': self.status == JobQueueStatusCodes.running,
            'result': self.status,
            'message': message
        }

    def stop(self, finish_running_jobs: bool = True, timeout: int = 60) -> dict:
        """
        Terminates the queue and reporting threads.
        :param finish_running_jobs: A boolean indicating whether to finish running jobs.
        :param timeout: The timeout in seconds to wait for running jobs to complete.
        :return:
        """

        from datetime import datetime, timezone

        logger.warning('Stopping the JobQueue.')
        self.status = JobQueueStatusCodes.stopping

        if not finish_running_jobs:
            logger.info('Ordering TaskChains to terminate.')

            # Notify the threads to stop
            for task_chain_id, task_chain in self.task_chains.items():
                task_chain.terminate()

        timeout_start_time = datetime.now()

        # Wait for the task chains to complete
        from CloudHarvestCoreTasks.tasks import TaskStatusCodes
        while (datetime.now() - timeout_start_time).total_seconds() < timeout:
            if all([task_chain.status not in (TaskStatusCodes.initialized, TaskStatusCodes.running) for task_chain in self.task_chains.values()]):
                logger.info('All task chains have completed.')
                self.status = JobQueueStatusCodes.stopped
                result = True
                break

        else:
            result = False

        # Record the stop time
        self.stop_time = datetime.now(tz=timezone.utc)

        return {
            'success': result,
            'result': str(self.status),
            'message': 'All task chains have completed.' if result else 'Timeout exceeded while waiting for task chains to complete.'
        }

    def report_task_chain_errors(self, task_chain_id: str, error: str) -> 'JobQueue':
        from CloudHarvestCoreTasks.silos import get_silo
        from json import dumps
        silo = get_silo('harvest-tasks')
        client = silo.connect()

        dead_task_chain_status = {
            'id': task_chain_id,
            'status': f'error: {error}'
        }

        client.set(task_chain_id, dumps(dead_task_chain_status))

        return self


def get_oldest_task_from_queue(client: StrictRedis,
                               accepted_chain_priorities: List[int]) -> Tuple[str, dict] or None:
    """
    Retrieves the oldest task from the queue.

    Arguments
    ---------
    silo (StrictRedis): The Redis silo to retrieve the task from.
    accepted_chain_priorities (List[int]): A list of accepted chain priorities.

    Returns
    -------
    Tuple[str, dict] or None: The oldest task from the Redis database as a tuple of task_id and task.
    (
        task_id (str): The ID of the task.
        task (dict): The task as a dictionary.
            {
                id (str) a UUID for the task
                name (str) the name of the task
                category (str) the category of the task
                config (dict) a dictionary of configuration parameters provided by the user or application
                created (datetime) the time the task was created
            }
    )
    """

    for priority in accepted_chain_priorities:
        queue_name = f'queue::{priority}'

        while True:
            # Check if this task queue is empty
            if client.llen(queue_name) == 0:
                # logger.debug(f'No priority {priority} tasks in the queue.')
                break

            task_queue_name = client.rpop(name=queue_name)

            if task_queue_name:
                # Get the task itself
                task = client.get(name=task_queue_name)

                # Remove the task from the queue so that it is not processed again
                client.delete(task_queue_name)

                if task:
                    from json import loads
                    logger.debug(f'Retrieved task `{task_queue_name}` from the queue.')

                    task_config = loads(task)

                    # Returns the first valid task from the queue, breaking the valid task and priority queue loops
                    return task_config['id'], task_config

                else:
                    # No task for this task id.
                    # This happens when a task expires. We skip it at that point and move on to the next
                    # task in the queue.
                    continue

    return None


class JobQueueStatusCodes:
    complete = 'complete'
    error = 'error'
    initialized = 'initialized'
    running = 'running'
    stopped = 'stopped'
    stopping = 'stopping'
    terminating = 'terminating'
