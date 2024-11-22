from blueprints.base import HarvestBlueprint
from flask import Response, jsonify, request
from json import loads
from typing import Any, List


# Blueprint Configuration
queue_blueprint = HarvestBlueprint(
    'queue_bp', __name__,
    url_prefix='/queue'
)

@queue_blueprint.route(rule='stop', methods=['GET'])
def stop() -> Response:
    pass

@queue_blueprint.route(rule='status', methods=['GET'])
def status() -> Response:
    pass

@queue_blueprint.route(rule='escalate', methods=['GET'])
def escalate() -> Response:
    pass


