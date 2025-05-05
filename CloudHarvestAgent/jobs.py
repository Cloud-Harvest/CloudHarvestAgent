from CloudHarvestCoreTasks.chains import BaseTaskChain

from CloudHarvestAgent.api import Api
from CloudHarvestCoreTasks.environment import Environment
from CloudHarvestCoreTasks.tasks import TaskStatusCodes
from CloudHarvestCoreTasks.tasks.redis import format_hset, unformat_hset

from datetime import datetime, timezone
from logging import getLogger
from threading import Thread

logger = getLogger('harvest')


class TaskChainQueue:
    def __init__(self, api: Api,
                 accepted_chain_priorities: list = None,
                 chain_progress_reporting_interval_seconds: int = 60,
                 chain_task_restrictions: list = None,
                 chain_timeout_seconds: int = 60,
                 queue_check_interval_seconds: int = 5,
                 max_chains: int = 10,
                 **kwargs
        ):

        from CloudHarvestCoreTasks.silos import get_silo

        # Remote resources
        self.api = api
        self.node_silo = get_silo('harvest-nodes').connect()    # Note status reports
        self.task_silo = get_silo('harvest-tasks').connect()    # Task queue, status, and results

        # Queue configuration
        self.accepted_chain_priorities = accepted_chain_priorities
        self.chain_progress_reporting_interval_seconds = chain_progress_reporting_interval_seconds
        self.chain_task_restrictions = chain_task_restrictions
        self.chain_timeout_seconds = chain_timeout_seconds
        self.queue_check_interval_seconds = queue_check_interval_seconds
        self.max_chains = max_chains

        self.start_time = None
        self.end_time = None
        self.status = JobQueueStatusCodes.initialized
        self.stop_time = None
        self.task_chains_processed = 0
        self.tasks = {}                         # {task_chain.redis_name: {'chain': task_chain, 'thread': thread}}
        self.worker_thread = None

    def detailed_status(self) -> dict:
        """
        Returns detailed status information about the JobQueue.
        :return:
        """

        from CloudHarvestCoreTasks.tasks import TaskStatusCodes

        result = {
            'chain_status': {
                str(status_code): sum(1 for task in self.tasks.keys() if task['chain'].status == status_code)
                for status_code in TaskStatusCodes.get_codes()
            },
            'duration': self.duration,
            'max_chains': self.max_chains,
            'start_time': self.start_time,
            'status': self.status,
            'stop_time': self.stop_time,
            'total_chains_in_queue': len(self.tasks.keys())
        }

        return result

    @property
    def duration(self) -> float:
        """
        Returns the duration of the JobQueue in seconds.
        :return:
        """
        from datetime import datetime, timezone

        if not self.start_time:
            return 0

        if self.stop_time:
            result = (self.stop_time - self.start_time).total_seconds()

        else:
            result = (datetime.now(tz=timezone.utc) - self.start_time).total_seconds()

        return result

    def _get_task(self) -> dict or None:
        for priority in self.accepted_chain_priorities:
            queue_name = f'queue::{priority}'

            while True:
                # Check if this task queue is empty
                if self.task_silo.llen(queue_name) == 0:
                    # logger.debug(f'No priority {priority} tasks in the queue.')
                    break

                task_queue_name = self.task_silo.rpop(name=queue_name)

                if task_queue_name:
                    # Get the task status
                    from CloudHarvestCoreTasks.tasks.redis import unformat_hset
                    task_status = self.task_silo.hget(name=task_queue_name, key='status')

                    if task_status != 'enqueued':
                        continue

                    # Since this task has not started HGETALL is safe because it won't contain the 'result' key, yet. Should
                    # the result key be present, it is possible that we'll consume a lot of resources by pulling large
                    # datasets out of Redis.
                    task = unformat_hset(self.task_silo.hgetall(name=task_queue_name))

                    if task:
                        logger.debug(f'Retrieved task `{task_queue_name}` from the queue.')

                        # Returns the first valid task from the queue, breaking the valid task and priority queue loops
                        return task

                    else:
                        # No task for this task id.
                        # This happens when a task expires. We skip it at that point and move on to the next
                        # task in the queue.
                        continue

        return None

    def _update_task_status(self, task_redis_nane: str, new_status: str):
        try:
            # Report the task chain instantiation to Redis
            self.task_silo.hset(name=task_redis_nane, key='status', value=new_status)

        except Exception as e:
            logger.error(f'{task_redis_nane} failed to report status to server: {e.args}')

    def _worker(self):
        """
        A thread that checks the Redis queue for new tasks and adds them to the JobQueue. It also reports the status
        of ongoing TaskChains to Redis.
        """

        while self.status == JobQueueStatusCodes.running:

            # Report status to Redis
            for task_object in self.tasks.values():
                task_chain = task_object['chain']

                try:
                    if task_chain.start and not task_chain.end:
                        from datetime import datetime
                        # Should the task chain exceed the timeout, issue a termination of the task chain
                        if (datetime.now() - task_chain.start).total_seconds() >= self.chain_timeout_seconds:
                            task_chain.status = TaskStatusCodes.terminating
                            logger.warning(
                                f'{task_chain.redis_name} terminating because it exceeded the timeout of {self.chain_timeout_seconds}.')

                    report_struct = task_chain.redis_struct()  # Redis data fields
                    report_struct['agent'] = Environment.get('agent.name')  # Agent name (unknown to the TaskChain)

                    # Report to Redis
                    self.task_silo.hset(name=task_chain.redis_name, mapping=format_hset(report_struct))

                except Exception as ex:
                    logger.error(f'{task_chain.redis_name} failed to report status to server: {ex}')

            # Add new tasks to the queue
            while True:
                # Check that the queue is not already full
                if len(self.tasks.keys()) <= self.max_chains:
                    # Attempt to pull a task from the queue
                    new_task = self._get_task()

                else:
                    # Escape because the queue is full
                    break

                # If we have a task, we need to process it
                if new_task:
                    try:
                        # Converts the task from a Redis hash to a dictionary
                        new_task = unformat_hset(new_task)

                        # Get the task chain configuration from the registry
                        from CloudHarvestCorePluginManager.registry import Registry
                        task_chain_class = Registry.find(result_key='cls',
                                                         name=new_task['name'],
                                                         category=new_task['category'])
                        # Instantiate the new task
                        from CloudHarvestCoreTasks.factories import task_chain_from_dict
                        task_chain = task_chain_from_dict(template=task_chain_class[0], **new_task['config'])
                        task_chain.id = new_task['id']
                        task_chain.parent = new_task['parent']

                        # Report the task chain instantiation to Redis
                        self._update_task_status(task_chain.redis_name, TaskStatusCodes.initialized)

                        # Create a new thread for this task chain
                        thread = Thread(target=task_chain.run, daemon=True)

                        # Add the task chain and task thread to the task pool
                        self.tasks[task_chain.redis_name] = {
                            'chain': task_chain,
                            'thread': thread
                        }

                        # Start the thread
                        thread.start()

                        self.task_chains_processed += 1

                        # Report task chain status to Redis
                        self._update_task_status(task_chain.redis_name, TaskStatusCodes.running)

                        logger.info(f'{task_chain.redis_name} started.')

                    except Exception as ex:
                        logger.error(f'Error while adding task chain {new_task["id"]} to the JobQueue: {ex.args}')

                        # Report the error to Redis
                        self._update_task_status(f'task::{new_task["id"]}', TaskStatusCodes.error)

                else:
                    # Escape the job queueing loop because the queue is empty
                    break

            # Remove completed tasks from the task pool
            for task_object in list(self.tasks.values()):
                if not task_object['thread'].is_alive():
                    task_chain = task_object['chain']
                    redis_name, final_status = task_chain.redis_name, task_chain.status

                    # Report the final status to Redis
                    self.task_silo.hset(name=task_chain.redis_name, key='status', value=task_chain.status)

                    # Remove it from the task pool
                    self.tasks.pop(task_chain.redis_name, None)

                    logger.info(f'{redis_name} removed from the task pool with status: {final_status}')

            from time import sleep
            logger.debug('queue worker cycle complete')
            sleep(self.queue_check_interval_seconds)

    def start(self) -> 'TaskChainQueue':
        """
        Start the worker thread if it is not already running.
        """

        self.start_time = datetime.now(tz=timezone.utc)
        self.end_time = None

        self.status = JobQueueStatusCodes.running

        if self.worker_thread:
            if self.worker_thread.is_alive():
                logger.warning('JobQueue is already running.')
                return self

        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

        return self

    def stop(self, terminate: bool = False) -> 'TaskChainQueue':
        """
        Stops the worker thread, if running.
        """
        # We only want to stop the worker thread if it is running, otherwise this is a no-op
        if self.status != JobQueueStatusCodes.running:
            logger.warning('JobQueue is not running.')
            return self

        logger.warning('Stopping the JobQueue.')
        self.status = JobQueueStatusCodes.terminating if terminate else JobQueueStatusCodes.stopping

        # Direct all task chains to terminate
        if terminate:
            for task_object in self.tasks.values():
                task_chain = task_object['chain']
                task_chain.terminate()

                self.task_silo.hset(name=task_chain.redis_name, key='status', value=TaskStatusCodes.terminating)

            while not all(not task_object['thread'].is_alive() for task_object in self.tasks.values()):
                # Wait for all task chains to terminate
                from time import sleep
                sleep(1)

        # Stop the worker thread
        if self.worker_thread:
            if self.worker_thread.is_alive():
                self.worker_thread.join()

        self.status = JobQueueStatusCodes.stopped
        self.stop_time = datetime.now(tz=timezone.utc)

        logger.warning(f'JobQueue stopped.')
        return self


class JobQueueStatusCodes:
    error = 'error'
    initialized = 'initialized'
    running = 'running'
    stopped = 'stopped'
    stopping = 'stopping'
    terminating = 'terminating'
