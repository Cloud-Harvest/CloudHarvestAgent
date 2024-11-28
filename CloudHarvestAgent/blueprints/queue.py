"""
The queue blueprint is responsible for managing the job queue.
"""

from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from flask import Response, jsonify, request


# Blueprint Configuration
queue_blueprint = HarvestAgentBlueprint(
    'queue_bp', __name__,
    url_prefix='/queue'
)

@queue_blueprint.route(rule='start', methods=['GET'])
def start() -> Response:
    """
    Starts the job queue.
    """
    from ..app import CloudHarvestAgent

    result = CloudHarvestAgent.job_queue.start()

    return jsonify(result)


@queue_blueprint.route(rule='stop', methods=['GET'])
def stop() -> Response:
    """
    Stops the job queue.
    """
    from ..app import CloudHarvestAgent

    result = CloudHarvestAgent.job_queue.stop()

    return jsonify(result)


@queue_blueprint.route(rule='status', methods=['GET'])
def status() -> Response:
    """
    Returns the status of the job queue.
    """
    from ..app import CloudHarvestAgent

    return jsonify(CloudHarvestAgent.job_queue.status())


# Escalation of tasks is done at the API level
# @queue_blueprint.route(rule='escalate/<task_chain_id>', methods=['GET'])
# def escalate(task_chain_id: str) -> Response:
#     pass
