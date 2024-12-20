"""
The home blueprint for the Harvest Agent. It handles the root endpoint and error handling.
"""

from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from flask import Response, jsonify

home_blueprint = HarvestAgentBlueprint(
    'home_bp', __name__
)


@home_blueprint.route(rule='/', methods=['GET'])
def home() -> Response:
    """
    The root endpoint for the Harvest Agent.
    """

    return jsonify('Successfully reached a CloudHarvestAgent instance.')


@home_blueprint.route('/favicon.ico')
def favicon():
    """
    The favicon endpoint.
    :return: No content
    """
    return '', 204

def not_implemented_error() -> Response:
    return jsonify({
        'error': 'Not implemented.'
    })
