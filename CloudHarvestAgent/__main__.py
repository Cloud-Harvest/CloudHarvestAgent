"""
Entrypoint for the CloudHarvestAgent
"""
# Imports objects which need to be registered by the CloudHarvestCorePluginManager
from __register__ import *


def main(**kwargs):
    from app import CloudHarvestAgent

    # Raw configuration for the agent
    CloudHarvestAgent.config = kwargs

    # Instantiate the Flask object
    from flask import Flask
    CloudHarvestAgent.app = Flask('CloudHarvestAgent')

    # Find all plugins and register their objects
    from CloudHarvestCorePluginManager.functions import register_objects
    register_objects()

    # Register the blueprints from this app and all plugins
    from CloudHarvestCorePluginManager.registry import Registry
    with CloudHarvestAgent.app.app_context():
        [
            CloudHarvestAgent.app.register_blueprint(api_blueprint)
            for api_blueprint in Registry.find(result_key='instances',
                                               name='harvest_blueprint',
                                               category='harvest_agent_blueprint')
            if api_blueprint is not None
        ]

    CloudHarvestAgent.app.run(**kwargs)

    print('Agent stopped')

if __name__ == '__main__':
    from yaml import load, SafeLoader

    agent_configuration = {}

    # Select the first file of the list
    for filename in ('../app/harvest.yaml', '../harvest.yaml'):
        from os.path import exists

        if exists(filename):
            with open('../harvest.yaml') as agent_file:
                agent_configuration = load(agent_file, Loader=SafeLoader)

            from flatten_json import flatten_preserve_lists

            # flatten_preserve_lists returns a List[Dict[str, Any]] but we want a Dict[str, Any]
            agent_configuration = flatten_preserve_lists(agent_configuration, separator='.')[0]

            break

    main(**agent_configuration)
