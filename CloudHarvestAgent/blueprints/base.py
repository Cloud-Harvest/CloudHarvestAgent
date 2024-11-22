from CloudHarvestCorePluginManager.decorators import register_definition

from flask import Blueprint
from logging import getLogger

logger = getLogger('harvest')


@register_definition(name='harvest_blueprint', category='blueprint', register_instances=True)
class HarvestBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        logger.info(f'Initializing Blueprint: {args[0]}')

        super().__init__(*args, **kwargs)
