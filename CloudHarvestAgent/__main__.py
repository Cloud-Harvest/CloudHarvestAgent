# Register all the classes which use the @register decorator
from __register__ import *


def main(**kwargs):
    from startup import load_logging
    logger = load_logging(log_destination=kwargs.get('logging.location'),
                          log_level=kwargs.get('logging.level'),
                          quiet=kwargs.get('logging.quiet'))

    logger.info('Agent configuration loaded successfully')

    from flask import Flask
    from .app import CloudHarvestAgent

    # Raw configuration for the agent
    CloudHarvestAgent.config = kwargs

    # Instantiate the Flask app
    CloudHarvestAgent.app = Flask('CloudHarvestAgent', instance_relative_config=False)
    CloudHarvestAgent.app.run(**kwargs)

    logger.warning('Agent stopped')

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
            agent_configuration = flatten_preserve_lists(agent_configuration, separator='.')

            break

    main(**agent_configuration)
