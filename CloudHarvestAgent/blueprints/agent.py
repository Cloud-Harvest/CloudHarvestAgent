"""
The agent blueprint is responsible for managing the Flask agent.s
"""

from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from flask import Response, jsonify, request
from logging import getLogger

logger = getLogger('harvest')

# Blueprint Configuration
agent_blueprint = HarvestAgentBlueprint(
    'agent_bp', __name__,
    url_prefix='/agent'
)

@agent_blueprint.route(rule='reload', methods=['GET'])
def reload() -> Response:
    """
    Reloads the agent's configuration, allowing configurations to be updated without stopping the agent.
    """
    # TODO: Implement this method

    return Response('501 - Not implemented', status=501)


@agent_blueprint.route(rule='shutdown', methods=['GET'])
def shutdown() -> Response:
    """
    Shuts down the agent.
    """

    from app import CloudHarvestNode
    from .base import safe_request_get_json

    request_json = safe_request_get_json(request)

    logger.warning('Received shutdown request.')

    result = CloudHarvestNode.job_queue.stop(finish_running_jobs=request_json.get('finish_running_jobs', True),
                                             timeout=request_json.get('timeout', 60))

    if result['result']:
        logger.info('Shutdown request completed.')

        # Gracefully shutdown the agent
        from sys import exit
        exit(0)

    else:

        logger.error(f'Shutdown request failed. {result["message"]}')
        return jsonify(result)
