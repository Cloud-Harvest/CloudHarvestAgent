from base import HarvestBlueprint
from flask import Response, jsonify, request

# Blueprint Configuration
tasks_blueprint = HarvestBlueprint(
    'tasks_bp', __name__,
    url_prefix='/tasks'
)

@tasks_blueprint.route(rule='shutdown/<task_id>', methods=['GET'])
def terminate(task_id: str) -> Response:
    """
    Stops the processing of a TaskChain based on its ID.

    Arguments:
        task_id (str): The ID of the TaskChain to stop.

    Returns:
        A Response object containing the result of the operation.
    """

    from ..app import CloudHarvestAgent

    task_object = CloudHarvestAgent.job_queue.get(task_id)

    if task_object is None:
        return jsonify({'error': 'Task not found.'})

    else:
        task_object.terminate()
        return jsonify({'message': 'Task terminated.'})


@tasks_blueprint.route(rule='status/<task_id>', methods=['GET'])
def status(task_id: str) -> Response:
    """
    Retrieves the status of a TaskChain based on its ID.

    Arguments:
        task_id (str): The ID of the TaskChain to retrieve the status of.

    Returns:
        A Response object containing the status of the TaskChain
    """

    from ..app import CloudHarvestAgent

    task_object = CloudHarvestAgent.job_queue.get(task_id)

    if task_object is None:
        return jsonify({'error': 'Task not found.'})

    else:
        return jsonify(task_object.status)
