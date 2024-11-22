from blueprints.base import HarvestBlueprint
from flask import Response, jsonify, request

# Blueprint Configuration
tasks_blueprint = HarvestBlueprint(
    'tasks_bp', __name__,
    url_prefix='/agent'
)

@tasks_blueprint.route(rule='shutdown', methods=['GET'])
def terminate() -> Response:
    from ..app import CloudHarvestAgent

    CloudHarvestAgent.job_queue.terminate()


@tasks_blueprint.route(rule='status', methods=['GET'])
def status() -> Response:
    pass

