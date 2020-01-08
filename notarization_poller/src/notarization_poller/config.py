#!/usr/bin/env python
"""Config for notarization poller.

Attributes:
    DEFAULT_CONFIG (frozendict): the default configuration
    log (logging.Logger): the log object for the module.

"""
import argparse
import logging
import logging.handlers
import os

from notarization_poller.constants import DEFAULT_CONFIG
from notarization_poller.exceptions import ConfigError
from scriptworker_client.client import init_config, _init_logging

log = logging.getLogger(__name__)


def update_logging_config(config, file_name="worker.log"):
    """Update python logging settings from config.

    * Use formatting from config settings.
    * Log to screen if ``verbose``
    * Add a rotating logfile from config settings.

    Args:
        config (dict): the running config

    """
    _init_logging(config)
    top_level_logger = logging.getLogger("")

    datefmt = config["log_datefmt"]
    fmt = config["log_fmt"]
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    if len(top_level_logger.handlers) == 0:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        top_level_logger.addHandler(handler)

    # Rotating log file
    os.makedirs(config["log_dir"], exist_ok=True)
    path = os.path.join(config["log_dir"], file_name)
    if config["watch_log_file"]:
        # If we rotate the log file via logrotate.d, let's watch the file
        # so we can automatically close/reopen on move.
        handler = logging.handlers.WatchedFileHandler(path)
    else:
        # Avoid using WatchedFileHandler during notarization poller unittests
        handler = logging.FileHandler(path)
    handler.setFormatter(formatter)
    top_level_logger.addHandler(handler)
    top_level_logger.addHandler(logging.NullHandler())


# get_config_from_cmdln {{{1
def _validate_config(config):
    if "..." in config.values():
        raise ConfigError("Uninitialized value in config!")


def get_config_from_cmdln(args, desc="Run notarization poller"):
    """Load config from the args.

    Args:
        args (list): the commandline args. Generally ``sys.argv[1:]``

    Returns:
        frozendict: the config

    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("config_path", type=str, nargs="?", default="poller.yaml", help="the path to the config file")
    parsed_args = parser.parse_args(args)
    config = init_config(config_path=parsed_args.config_path, default_config=DEFAULT_CONFIG, validator_callback=_validate_config)
    update_logging_config(config)
    return config
