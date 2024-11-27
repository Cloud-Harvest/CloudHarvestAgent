from blueprints.base import HarvestBlueprint, logger
from flask import Response, jsonify, request
from json import loads
from logging import getLogger

logger = getLogger('harvest')

# Blueprint Configuration
agent_blueprint = HarvestBlueprint(
    'agent_bp', __name__,
    url_prefix='/agent'
)

@agent_blueprint.route(rule='shutdown', methods=['GET'])
def shutdown() -> Response:
    from ..app import CloudHarvestAgent

    request_json = loads(request.get_json())

    logger.warning('Received shutdown request.')

    result = CloudHarvestAgent.job_queue.stop(finish_running_jobs=request_json.get('finish_running_jobs', True),
                                              timeout=request_json.get('timeout', 60))

    if result['result']:
        logger.info('Shutdown request completed.')

        # Gracefully shutdown the agent
        from sys import exit
        exit(0)

    else:

        logger.error(f'Shutdown request failed. {result["message"]}')
        return jsonify(result)
