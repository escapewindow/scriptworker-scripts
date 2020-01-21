#!/usr/bin/env python
"""Treescript task functions."""
import logging

from treescript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


VALID_ACTIONS = {"tag", "version_bump", "l10n_bump", "push"}

DONTBUILD_MSG = " DONTBUILD"
CLOSED_TREE_MSG = " CLOSED TREE"


# get_source_repo {{{1
def get_metadata_source_repo(task):
    """Get the source repo from the task metadata.

    Assumes `task['metadata']['source']` exists and is a link to a mercurial file on
    hg.mozilla.org (over https)

    Args:
        task: the task definition.

    Returns:
        str: url, including https scheme, to mercurial repository of the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    source = task.get("metadata", {}).get("source", None)
    if not source:
        raise TaskVerificationError("No source, how did that happen")
    if not source.startswith("https://hg.mozilla.org/"):
        raise TaskVerificationError("Unable to operate on sources not in hg.mozilla.org")
    parts = source.split("/file/")
    if len(parts) < 2:
        raise TaskVerificationError("Source url is in unexpected format")
    return parts[0]


def get_source_repo(task):
    """Get the source repo from the task payload, falling back to the metadata.

    First looks for `task['payload']['source_repo']`, then falls back to
    ``get_metadata_source_repo``.

    Args:
        task: the task definition.

    Returns:
        str: url, including https scheme, to mercurial repository of the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    if task["payload"].get("source_repo"):
        return task["payload"]["source_repo"]
    return get_metadata_source_repo(task)


def get_short_source_repo(task):
    """Get the name of the source repo, e.g. mozilla-central.

    Args:
        task: the task definition.

    Returns:
        str: the name of the source repo

    """
    source_repo = get_source_repo(task)
    parts = source_repo.split("/")
    return parts[-1]


# get_branch {{{1
def get_branch(task, default=None):
    """Get the optional branch from the task payload.

    This is largely for relbranch support in mercurial.

    Args:
        task (dict): the running task

    Returns:
        None: if no branch specified
        str: the branch specified in the task

    """
    return task.get("payload", {}).get("branch", default)


# get_tag_info {{{1
def get_tag_info(task):
    """Get the tag information from the task metadata.

    Assumes task['payload']['tag_info'] exists and is in the proper format.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    tag_info = task.get("payload", {}).get("tag_info")
    if not tag_info:
        raise TaskVerificationError("Requested tagging but no tag_info in payload")
    return tag_info


# get_version_bump_info {{{1
def get_version_bump_info(task):
    """Get the version bump information from the task metadata.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    version_info = task.get("payload", {}).get("version_bump_info")
    if not version_info:
        raise TaskVerificationError("Requested version bump but no version_bump_info in payload")
    return version_info


# get_l10n_bump_info {{{1
def get_l10n_bump_info(task):
    """Get the l10n bump information from the task metadata.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    l10n_bump_info = task.get("payload", {}).get("l10n_bump_info")
    if not l10n_bump_info:
        raise TaskVerificationError("Requested l10n bump but no l10n_bump_info in payload")
    return l10n_bump_info


# get dontbuild {{{1
def get_dontbuild(task):
    """Get information on whether DONTBUILD needs to be attached at the end of commit message.

    Args:
        task: the task definition.

    Returns:
        boolean: the dontbuild info as passed to the task payload (defaulted to false).

    """
    return task.get("payload", {}).get("dontbuild", False)


# get_ignore_closed_tree {{{1
def get_ignore_closed_tree(task):
    """Get information on whether CLOSED TREE needs to be added to the commit message.

    Args:
        task: the task definition.

    Returns:
        boolean: the ``ignore_closed_tree`` info as passed to the task payload (defaulted to false).

    """
    return task.get("payload", {}).get("ignore_closed_tree", False)


# task_action_types {{{1
def task_action_types(config, task):
    """Extract task actions from task payload.

    Args:
        config (dict): the running config.
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if unknown actions are specified.

    Returns:
        set: the set of specified actions

    """
    actions = set(task["payload"].get("actions", []))
    log.info("Action requests: %s", actions)
    invalid_actions = actions - VALID_ACTIONS
    if len(invalid_actions) > 0:
        raise TaskVerificationError("Task specified invalid actions: {}".format(invalid_actions))

    return actions


# is_dry_run {{{1
def should_push(task, actions):
    """Determine whether this task should push the changes it makes.

    If `dry_run` is true on the task, there will not be a push.
    Otherwise, if `push` is specified, that determines if there should be a push.
    Otherwise, there is a push if the `push` action is specified.

    Args:
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        bool: whether this task should push

    """
    dry_run = task["payload"].get("dry_run", False)
    push = task["payload"].get("push")
    push_action = "push" in actions
    if dry_run:
        log.info("Not pushing changes, dry_run was forced")
        return False
    elif push is not None:
        if not push and push_action:
            log.warning("Push disabled, but push action provided; ignore push action")
        return push
    elif push_action:
        log.warning("Specifying push as an action is deprecated; task.payload.push instead.")
        return True
    else:
        log.info("Not pushing changes, no push requested")
        return False
