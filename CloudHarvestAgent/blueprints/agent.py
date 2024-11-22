from blueprints.base import HarvestBlueprint
from flask import Response, jsonify, request

# Blueprint Configuration
agent_blueprint = HarvestBlueprint(
    'agent_bp', __name__,
    url_prefix='/agent'
)

@agent_blueprint.route(rule='shutdown', methods=['GET'])
def shutdown() -> Response:
    from ..agent import JobQueue


@agent_blueprint.route(rule='status', methods=['GET'])
def status() -> Response:
    pass

