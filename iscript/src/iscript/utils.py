#!/usr/bin/env python
"""Shared functions for iScript.

Attributes:
    log (logging.Logger): the log object for the module

"""
import logging

from scriptworker_client.utils import run_command
from iscript.exceptions import IScriptError

log = logging.getLogger(__name__)

_CERT_TYPE_TO_KEY_CONFIG = {
    "dep-signing": "dep",
    "nightly-signing": "nightly",
    "release-signing": "release",
}


def task_cert_type(config, task):
    """Get the signing cert type from the task scopes.

    Args:
        config (dict): the running config
        task (dict): the running task

    Returns:
        str: the cert type, e.g. ``dep-signing``

    """
    cert_prefix = "{}cert:".format(config["taskcluster_scope_prefix"])
    cert_scopes = [i for i in task["scopes"] if i.startswith(cert_prefix)]
    if len(cert_scopes) > 1:
        raise IScriptError("Too many cert scopes found! {}".format(cert_scopes))
    if len(cert_scopes) < 1:
        raise IScriptError("Unable to find a cert scope! {}".format(task["scopes"]))
    return cert_scopes[0].replace(cert_prefix, "")


def get_key_config(config, task, base_key="mac_config"):
    """Sanity check the task scopes and return the appropriate ``key_config``.

    The ``key_config`` is, e.g. the ``config.mac_config.dep`` dictionary,
    for mac dep-signing.

    Args:
        config (dict): the running config
        task (dict): the running task
        base_key (str, optional): the base key in the dictionary. Defaults to
            ``mac_config``.

    Raises:
        IScriptError: on failure to verify the scopes.

    Returns:
        dict: the ``key_config``

    """
    try:
        cert_type = task_cert_type(config, task)
        return config[base_key][_CERT_TYPE_TO_KEY_CONFIG[cert_type]]
    except KeyError as exc:
        raise IScriptError("get_key_config error: {}".format(str(exc))) from exc


# chown {{{1
async def chown(path, user, group=None, exception=IScriptError, **kwargs):
    """Wrap a ``sudo chown`` call.

    Args:
        path (str): the path to chown
        user (str): the user or UID to chown to
        group (str, optional): the group to chown to, if specified. Defaults
            to ``None``.
        exception (Exception, optional): the exception class to raise on
            failure. Defaults to ``IScriptError``.
        kwargs: the kwargs to send to ``run_command``.

    """
    command = ["sudo", "chown", "-R"]
    if group is not None:
        command.append(f"{user}:{group}")
    else:
        command.append(user)
    command.append(path)
    await run_command(command, exception=exception, **kwargs)
