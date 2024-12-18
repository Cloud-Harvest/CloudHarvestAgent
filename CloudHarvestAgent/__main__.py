"""
Entrypoint for the CloudHarvestAgent
"""
# Imports objects which need to be registered by the CloudHarvestCorePluginManager
from __register__ import *


def main(**kwargs):
    from app import CloudHarvestNode

    # Raw configuration for the agent
    CloudHarvestNode.config = kwargs

    # Instantiate the Flask object
    from flask import Flask
    CloudHarvestNode.flask = Flask('CloudHarvestAgent')

    # Find all plugins and register their objects and templates
    from CloudHarvestCorePluginManager import register_all
    register_all()

    # Register the blueprints from this app and all plugins
    from CloudHarvestCorePluginManager.registry import Registry
    with CloudHarvestNode.flask.app_context():
        [
            CloudHarvestNode.flask.register_blueprint(api_blueprint)
            for api_blueprint in Registry.find(result_key='instances',
                                               name='harvest_blueprint',
                                               category='harvest_agent_blueprint')
            if api_blueprint is not None
        ]

    CloudHarvestNode.run(**kwargs)

    print('Agent stopped')

if __name__ == '__main__':
    from app import load_configuration_from_file
    main(**load_configuration_from_file())
