from CloudHarvestCoreTasks.blueprints import HarvestAgentBlueprint
from flask import Response, jsonify
from logging import getLogger

logger = getLogger('harvest')


# Blueprint Configuration
templates_blueprint = HarvestAgentBlueprint(
    'tasks_bp', __name__,
    url_prefix='/templates'
)


@templates_blueprint.route(rule='describe_templates/<template_category?>', methods=['GET'])
def describe_templates(template_category: str = None) -> Response:
    """
    Returns the registry entry for all templates in the specified category. When no category is specified, it
    returns all templates.

    Arguments
        template_category (str, optional): The category of the templates to retrieve. If None, retrieves all templates.

    Returns:
        A Response object containing the templates data and a success flag.
    """

    from CloudHarvestCorePluginManager.registry import Registry

    reason = 'OK'
    templates = None
    success = False

    try:
        templates = Registry.find(
            result_key='*',
            category=f'template_{template_category}' if template_category else 'template_.*'
        )

        if len(templates) == 0:
            reason = f'No templates found for category: {template_category}' if template_category else 'No templates found.'

        else:
            success = True

    except Exception as ex:
        reason = str(ex)

    return jsonify(
        {
            'success': success,
            'data': templates,
            'reason': reason
        }
    )


@templates_blueprint.route(rule='get_template/<template_category>/<template_name>', methods=['GET'])
def get_template(template_category: str, template_name: str) -> Response:
    """
    Retrieves a template based on its category and name.

    Arguments:
        template_category (str): The category of the template.
        template_name (str): The name of the template.

    Returns:
        A Response object containing the template data.
    """

    reason = 'OK'
    template = None
    success = False

    try:
        from CloudHarvestCorePluginManager.registry import Registry
        template = Registry.find(result_key='cls',
                                 category=f'template_{template_category}',
                                 name=template_name)

        if len(template) == 0:
            reason = f'Template {template_category}/{template_name} not found.'

        elif len(template) == 1:
            template = template[0]
            success = True

        else:
            reason = 'Multiple templates found with the same name. Please specify a unique template name.'
            success = True


    except Exception as ex:
        reason = str(ex)

    return jsonify(
        {
            'success': success,
            'data': template,
            'reason': reason
        }
    )

@templates_blueprint.route(rule='list_templates/<template_category?>', methods=['GET'])
def list_templates(template_category: str = None) -> Response:
    """
    Returns a list of templates based on the specified category. When no category is specified, it returns all templates.
    """

    from CloudHarvestCorePluginManager.registry import Registry

    reason = 'OK'
    templates = None
    success = False

    try:
        templates = Registry.find(
            result_key='name',
            category=f'template_{template_category}' if template_category else 'template_.*'
        )

        if len(templates) == 0:
            reason = f'No templates found for category: {template_category}' if template_category else 'No templates found.'

        else:
            success = True

    except Exception as ex:
        reason = str(ex)

    return jsonify(
        {
            'success': success,
            'data': templates,
            'reason': reason
        }
    )

@templates_blueprint.route(rule='reload_templates', methods=['GET'])
def reload_templates() -> Response:
    """
    Reloads the templates from disks and returns the number of templates found. Useful for refreshing templates after changes.

    Returns:
        A Response object containing the number of templates found and a success flag.
    """

    from CloudHarvestCorePluginManager.registry import Registry, register_all

    reason = 'OK'
    success = False
    templates = []

    try:
        # Find all plugins and register their objects and templates
        register_all()
        templates = list_templates().get_json().get('data', [])

    except Exception as ex:
        reason = str(ex)

    return jsonify(
        {
            'success': success,
            'data': len(templates),
            'reason': reason
        }
    )
