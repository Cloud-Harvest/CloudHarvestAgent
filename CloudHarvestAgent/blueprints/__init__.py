"""
__init__.py is a special Python file that is executed when a directory is imported as a package.

This file is used to import all the blueprints into the Flask app.
"""

from agent import agent_blueprint
from home import home_blueprint
from queue import queue_blueprint
from tasks import tasks_blueprint
