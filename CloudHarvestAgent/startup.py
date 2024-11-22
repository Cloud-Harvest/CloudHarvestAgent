from .agent import Api
from logging import Logger, getLogger

logger = getLogger('harvest')


def load_logging(log_destination: str = './app/logs/', log_level: str = 'info', quiet: bool = False) -> Logger:
    """
    This method configures logging for the Agent.

    Arguments
    log_destination (str, optional): The destination directory for the log file. Defaults to './app/logs/'.
    log_level (str, optional): The logging level. Defaults to 'info'.
    quiet (bool, optional): Whether to suppress console output. Defaults to False.
    """
    level = log_level

    from logging import getLogger, Formatter, StreamHandler, DEBUG
    from logging.handlers import RotatingFileHandler

    # startup
    new_logger = getLogger(name='harvest')

    from importlib import import_module
    lm = import_module('logging')
    log_level_attribute = getattr(lm, level.upper())

    # clear existing log handlers anytime this library is called
    [new_logger.removeHandler(handler) for handler in new_logger.handlers]

    # formatting
    log_format = Formatter(fmt='[%(asctime)s][%(levelname)s][%(filename)s] %(message)s')

    # file handler
    from pathlib import Path
    from os.path import abspath, expanduser
    _location = abspath(expanduser(log_destination))

    # make the destination log directory if it does not already exist
    Path(_location).mkdir(parents=True, exist_ok=True)

    # configure the file handler
    from os.path import join
    fh = RotatingFileHandler(join(_location, 'agent.log'), maxBytes=10000000, backupCount=5)
    fh.setFormatter(fmt=log_format)
    fh.setLevel(DEBUG)

    new_logger.addHandler(fh)

    if quiet is False:
        # stream handler
        sh = StreamHandler()
        sh.setFormatter(fmt=log_format)
        sh.setLevel(log_level_attribute)
        new_logger.addHandler(sh)

    new_logger.setLevel(log_level_attribute)

    new_logger.debug('logging: enabled')

    return new_logger
