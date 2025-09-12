from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from flask import Response, jsonify, request
from logging import getLogger

logger = getLogger('harvest')


# Blueprint Configuration
templates_blueprint = HarvestAgentBlueprint(
    'templates_bp', __name__,
    url_prefix='/templates'
)

@templates_blueprint.route(rule='/get_template/<template_type>/<template_name>', methods=['GET'])
def get_template(template_type: str, template_name: str) -> Response:
    from CloudHarvestCorePluginManager.registry import Registry
    template_definition = Registry.find(result_key='cls', category=template_type, name=template_name, limit=1)

    if template_definition:
        return jsonify(template_definition[0])

    else:
        return Response({'error': f'Template `{template_name}` of type `{template_type}` not found.'}, status=404)

@templates_blueprint.route(rule='/list_templates', methods=['GET'])
def list_templates() -> Response:
    pass

