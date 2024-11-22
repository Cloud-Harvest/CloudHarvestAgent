from logging import getLogger
from typing import Dict, List, Literal

from CloudHarvestCoreTasks.silos import get_silo
from CloudHarvestCoreTasks.tasks import BaseTaskChain, TaskStatusCodes

logger = getLogger('harvest')


class JobQueue(Dict[str, BaseTaskChain]):
    """
    The JobQueue class is responsible for checking the Redis queue for new tasks and adding them to the queue. It also
    reports the status of any running task chains to the harvest-agent-status silo.
    """
    from .api import Api

    def __init__(self,
                 api: Api,
                 accepted_chain_priorities: List[int],
                 chain_progress_reporting_interval_seconds: int,
                 chain_task_restrictions: List[str],
                 chain_timeout_seconds: int,
                 queue_check_interval_seconds: int,
                 max_chain_delay_seconds: int,
                 max_running_chains: int,
                 max_chain_queue_depth: int,
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
        max_chain_delay_seconds (int): The maximum delay in seconds for a chain.
        max_running_chains (int): The maximum number of running chains.
        max_chain_queue_depth (int): The maximum depth of the chain queue.
        reporting_interval_seconds (int): The interval in seconds for reporting.

        Additional Parameters:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

        """

        super().__init__(*args, **kwargs)

        # Api configuration
        self.api = api

        # Silo configurations retrieved from the API
        self._silos = {}

        # Queue configuration
        self.accepted_chain_priorities = accepted_chain_priorities
        self.chain_progress_reporting_interval_seconds = chain_progress_reporting_interval_seconds
        self.chain_task_restrictions = chain_task_restrictions
        self.chain_timeout_seconds = chain_timeout_seconds
        self.queue_check_interval_seconds = queue_check_interval_seconds
        self.max_chain_delay_seconds = max_chain_delay_seconds
        self.max_running_chains = max_running_chains
        self.max_chain_queue_depth = max_chain_queue_depth
        self.reporting_interval_seconds = reporting_interval_seconds

        # Threads
        self._reporting_thread = None
        self._queue_check_thread = None

        # Programmatic attributes
        from datetime import datetime, timezone
        self.start_time = datetime.now(tz=timezone.utc)
        self.status = TaskStatusCodes.initialized
        self.stop_time = None


    def _on_chain_complete(self, task_chain_id: str):
        """
        A callback that is called when a task chain completes. It sends the chain's final results to the harvest-agent-results
        silo, then removes the task chain from the JobQueue.
        :return:
        """
        from CloudHarvestCoreTasks.silos import get_silo

        # Update the status of the task chain to the harvest-agent-queue-status silo
        argent_queue_status = get_silo('harvest-agent-queue-status')

        # Send the final results to the harvest-agent-results silo
        pass

        # Remove the task chain from the JobQueue
        self.pop(task_chain_id, None)

    def _thread_reporting(self):
        """
        A thread that reports the progress of the task chains to the API.
        :return:
        """

        from json import dumps
        from redis import StrictRedis
        from time import sleep

        while True:
            reporting_silo = StrictRedis(**self._silos.get('harvest-jobs-status'))

            try:

                for task_chain_id, task_chain in list(self.items()):
                    # Report the progress of the task chain to the API
                    reporting_silo.set(task_chain_id, dumps(task_chain.detailed_progress()))

                    # Automatically expire the key after 10 reporting intervals
                    reporting_silo.expire(task_chain_id, self.reporting_interval_seconds * 10)

                    # Escape the loop if the task chain is complete or terminating
                    if self.status in [TaskStatusCodes.complete, TaskStatusCodes.terminating]:
                        break

            except Exception as e:
                logger.error(f'Error while reporting chain progress: {e.args}')

            else:
                logger.info('Chain progress reported.')

            finally:
                sleep(self.reporting_interval_seconds)

    def _thread_check_queue(self):
        """
        A thread that checks the Redis queue for new tasks and adds them to the JobQueue.
        :return:
        """
        from redis import StrictRedis
        from time import sleep

        while self.status != TaskStatusCodes.terminating:
            for allowed_queue_priority in self.accepted_chain_priorities:


                # Escape the loop if the task chain is complete or terminating
                if self.status in [TaskStatusCodes.complete, TaskStatusCodes.terminating]:
                    break

            sleep(self.queue_check_interval_seconds)

    def get_chain_status(self, task_chain_id: str) -> dict:
        """
        Retrieves the status of a task chain.
        :return:
        """

        task_chain: BaseTaskChain = self.get(task_chain_id)

        if task_chain is None:
            raise ValueError(f'Task chain with ID {task_chain_id} not found.')

        return {
            task_chain_id: task_chain.detailed_progress()
        }

    @staticmethod
    def prepare_redis_payload(dictionary: dict) -> dict:
        """
        Prepares a dictionary to be stored in Redis by converting incompatible types to strings.
        :param dictionary: The dictionary to prepare.
        :return: The prepared dictionary.
        """
        from flatten_json import flatten_preserve_lists, unflatten

        separator = '.'

        flat_dictionary = flatten_preserve_lists(dictionary, separator=separator)

        for key, value in flat_dictionary.items():
            if not isinstance(value, (str, int, float, bool)):
                flat_dictionary[key] = str(value)

        return unflatten(flat_dictionary, separator=separator)

    def start(self) -> str:
        """
        Starts the job queue process.
        :return: the status of the job queue.
        """

        self.status = JobQueueStatusCodes.running

        from threading import Thread
        self._reporting_thread = Thread(target=self._thread_reporting, daemon=True)
        self._queue_check_thread = Thread(target=self._thread_check_queue, daemon=True)

        return self.status

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

        # Prevents the JobQueue from starting new tasks
        self._queue_check_thread.join()

        if not finish_running_jobs:
            logger.info('Ordering TaskChains to terminate.')

            # Notify the threads to stop
            for task_chain_id, task_chain in self.items():
                task_chain.terminate()

        timeout_start_time = datetime.now()

        # Wait for the task chains to complete
        from CloudHarvestCoreTasks.tasks import TaskStatusCodes
        while (datetime.now() - timeout_start_time).total_seconds() < timeout:
            if all([task_chain.status not in (TaskStatusCodes.initialized, TaskStatusCodes.running) for task_chain in self.values()]):
                logger.info('All task chains have completed.')
                self.status = JobQueueStatusCodes.stopped
                result = True
                break

        else:
            result = False

        # Record the stop time
        self.stop_time = datetime.now(tz=timezone.utc)

        return {
            'result': result,
            'message': 'All task chains have completed.' if result else 'Timeout exceeded while waiting for task chains to complete.'
        }

class JobQueueStatusCodes:
    complete = 'complete'
    error = 'error'
    initialized = 'initialized'
    running = 'running'
    stopped = 'stopped'
    stopping = 'stopping'
    terminating = 'terminating'
