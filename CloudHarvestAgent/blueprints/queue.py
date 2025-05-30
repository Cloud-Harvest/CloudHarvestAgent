"""
The queue blueprint is responsible for managing the job queue.
"""

from CloudHarvestAgent.blueprints.home import not_implemented_error
from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from CloudHarvestCoreTasks.environment import Environment

from flask import Response, jsonify


# Blueprint Configuration
queue_blueprint = HarvestAgentBlueprint(
    'queue_bp', __name__,
    url_prefix='/queue'
)

@queue_blueprint.route(rule='inject', methods=['POST'])
def inject():
    """
    Accepts a serialized TaskChain, puts it in the JobQueue, and immediately starts it. This operation bypasses the
    JobQueue's scheduling and limit mechanisms. This is useful when a task chain needs to be executed immediately.

    :return: uuid of the instantiated TaskChain
    """

    # TODO: Implement this method
    return not_implemented_error()


@queue_blueprint.route(rule='start', methods=['GET'])
def start() -> Response:
    """
    Starts the job queue.
    """
    job_queue = Environment.get('queue_object')
    result = job_queue.start()

    return jsonify(result)


@queue_blueprint.route(rule='stop', methods=['GET'])
def stop() -> Response:
    """
    Stops the job queue.
    """
    job_queue = Environment.get('queue_object')
    result = job_queue.stop()

    return jsonify(result)


@queue_blueprint.route(rule='status', methods=['GET'])
def status() -> Response:
    """
    Returns a detailed status of the job queue.
    """
    job_queue = Environment.get('queue_object')
    result = job_queue.detailed_status()

    return jsonify({
        'success': bool(result),
        'message': 'OK' if result else 'No status available',
        'result': result
    })
