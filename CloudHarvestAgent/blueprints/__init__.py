"""
__init__.py is a special Python file that is executed when a directory is imported as a package.

This file is used to import all the blueprints into the Flask app.
"""

from CloudHarvestAgent.blueprints.agent import agent_blueprint
from CloudHarvestAgent.blueprints.home import home_blueprint
from CloudHarvestAgent.blueprints.queue import queue_blueprint
from CloudHarvestAgent.blueprints.tasks import tasks_blueprint
from CloudHarvestAgent.blueprints.templates import templates_blueprint
