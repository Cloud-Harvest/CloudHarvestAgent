import unittest
from CloudHarvestAgent import Api, JobQueue, JobQueueStatusCodes
from CloudHarvestCoreTasks.tasks import BaseTaskChain, TaskStatusCodes

class TestJobQueue(unittest.TestCase):
    def setUp(self):
        self.api = Api(host='localhost', port=8000, token='test_token')
        self.job_queue = JobQueue(
            api=self.api,
            accepted_chain_priorities=[1, 2, 3],
            chain_progress_reporting_interval_seconds=10,
            chain_task_restrictions=[],
            chain_timeout_seconds=60,
            queue_check_interval_seconds=5,
            max_chain_delay_seconds=30,
            max_chains=5,
            max_chain_queue_depth=10,
            reporting_interval_seconds=15
        )

    def test_start(self):
        result = self.job_queue.start()
        self.assertEqual(result['result'], JobQueueStatusCodes.running)
        self.assertEqual(result['message'], 'JobQueue started successfully.')

    def test_stop(self):
        self.job_queue.start()
        result = self.job_queue.stop(finish_running_jobs=True, timeout=10)
        self.assertTrue(result['result'])
        self.assertEqual(result['message'], 'All task chains have completed.')

    def test_get_chain_status(self):
        task_chain_id = 'test_chain_id'
        task_chain = BaseTaskChain()
        task_chain.status = TaskStatusCodes.running
        self.job_queue[task_chain_id] = task_chain

        status = self.job_queue.get_chain_status(task_chain_id)
        self.assertEqual(status[task_chain_id]['status'], TaskStatusCodes.running)

    def test_prepare_redis_payload(self):
        payload = {'key1': 'value1', 'key2': {'subkey': 'subvalue'}}
        prepared_payload = self.job_queue.prepare_redis_payload(payload)
        self.assertEqual(prepared_payload, {'key1': 'value1', 'key2.subkey': 'subvalue'})

    def test_thread_check_queue(self):
        # This test will check if the queue checking thread can be started and stopped
        self.job_queue._thread_check_queue()
        self.assertTrue(self.job_queue._check_queue_thread.is_alive())

    def test_thread_reporting(self):
        # This test will check if the reporting thread can be started and stopped
        self.job_queue._thread_reporting()
        self.assertTrue(self.job_queue._reporting_thread.is_alive())

if __name__ == '__main__':
    unittest.main()