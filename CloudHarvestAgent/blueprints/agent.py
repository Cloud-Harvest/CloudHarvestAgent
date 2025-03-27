"""
The agent blueprint is responsible for managing the Flask agent.s
"""
from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from flask import Response, jsonify, request
from logging import getLogger
from CloudHarvestAgent.blueprints.home import not_implemented_error

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

    return not_implemented_error()


@agent_blueprint.route(rule='install_plugin', methods=['GET'])
def install_plugin() -> Response:
    """
    Installs a plugin from the plugins.txt file.

    Arguments
    url_or_package_name (str) - the URL or package name of the plugin to install.
    branch (str, optional) - the branch of the plugin to install. Defaults to 'main'.
    """

    from CloudHarvestCorePluginManager.plugins import generate_plugins_file, install_plugins, read_plugins_file

    message = 'OK'
    result = []

    try:
        from CloudHarvestAgent.blueprints.base import safe_request_get_json
        request_json = safe_request_get_json(request)

        url_or_package_name = request_json.get('url_or_package_name')
        branch = request_json.get('branch') or 'main'

        if not url_or_package_name:
            raise ValueError('`url_or_package_name` is required')

        plugins = read_plugins_file() or []

        plugins.append(
            {
                'url_or_package_name': url_or_package_name,
                'branch': branch
            }
        )

        # Generate the plugins file
        generate_plugins_file(plugins=plugins)

        # Install the plugins
        install_plugins()

        # Reread the plugins file
        result = read_plugins_file() or []

    except Exception as ex:
        message = f'Failed to install plugin: {str(ex)}'

    finally:
        return jsonify({
            'success': True if message == 'OK' else False,
            'message': message,
            'result': result
        })


@agent_blueprint.route(rule='/list_plugins', methods=['GET'])
def list_plugins() -> Response:
    """
    Lists the plugins which should be installed by the agent.
    """

    from CloudHarvestCorePluginManager.plugins import read_plugins_file

    message = 'OK'
    result = []

    try:
        result = read_plugins_file() or []

    except Exception as ex:
        message = f'Failed to read plugins file: {str(ex)}'

    finally:
        return jsonify({
            'success': True if message == 'OK' else False,
            'message': 'OK',
            'result': result
        })

# @agent_blueprint.route(rule='shutdown', methods=['GET'])
# def shutdown() -> Response:
#     """
#     Shuts down the agent.
#     """
#
#     from app import CloudHarvestNode
#     from .base import safe_request_get_json
#
#     request_json = safe_request_get_json(request)
#
#     logger.warning('Received shutdown request.')
#
#     result = CloudHarvestNode.job_queue.stop(finish_running_jobs=request_json.get('finish_running_jobs', True),
#                                              timeout=request_json.get('timeout', 60))
#
#     if result['result']:
#         logger.info('Shutdown request completed.')
#
#         # Gracefully shutdown the agent
#         from sys import exit
#         exit(0)
#
#     else:
#
#         logger.error(f'Shutdown request failed. {result["message"]}')
#         return jsonify(result)
