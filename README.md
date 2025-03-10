# Cloud Harvest Agent
The Cloud Harvest Agent is responsible for collecting data or performing asynchronous tasks on behalf of the Cloud Harvest Platform.

## Job Queue
Agents manage their own internal job queue, which is a collection of TaskChains that are running. Tasks are either
directly assigned or retrieved from a shared queue silo named `harvest-task-queue`. When an Agent picks up a task, it
is removed from the queue and placed in the Agent's job queue. The Agent then processes the TaskChain and stores the
results in the `harvest-task-results` silo, if applicable.

## Endpoints
The Agent exposes the following endpoints:

| Endpoint                     | HTTP Method | Description                                                                                                      |
|------------------------------|-------------|------------------------------------------------------------------------------------------------------------------|
| `/`                          | GET         | Verifies that the endpoint is a Harvest Agent instance.                                                          |
| `/agent`                     |             | Agent endpoints control the Flask API itself.                                                                    |
| `/agent/reload`              | GET         | Reloads some configuration information.                                                                          |
| `/agent/shutdown`            | GET         | Attempts to stop the agent process.                                                                              |
| `/queue`                     |             | Queue endpoints affect the task queue.                                                                           |
| `/queue/inject`              | GET         | Submits a task to the JobQueue directly, bypassing the shared JobQueue located in the `harvest-task-queue` silo. |
| `/queue/start`               | GET         | Starts the job queue.                                                                                            |
| `/queue/status`              | GET         | Provides details about the job queue                                                                             |
| `/queue/stop`                | GET         | Stops the job queue                                                                                              |
| `/tasks/`                    |             |                                                                                                                  |
| `/tasks/status/<task_id>`    | GET         | Retrieve the status of a task                                                                                    |
| `/tasks/terminate/<task_id>` | GET         | Stop a running task                                                                                              |

### Return Values
All endpoints will return a JSON object with one or more of the following keys:

| Key      | Description                                                                                                                                                                                                                                |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `error`  | If an error occurred, this will contain a string describing the error.                                                                                                                                                                     |
| `meta`   | This is a dictionary containing metadata about the operation such as the time it took to complete, a count of records, or anything else that might be useful to report. Metadata is intended to be simple, small, and contextually useful. |
| `result` | This is the result of the operation. It may be of any serialized type.                                                                                                                                                                     |
