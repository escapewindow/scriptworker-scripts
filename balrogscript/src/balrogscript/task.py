import json
import logging
import os
import re
import sys

import jsonschema

from balrogscript.constants import VALID_ACTIONS

log = logging.getLogger(__name__)


def validate_task_schema(script_config, task_definition, action):
    """Perform a schema validation check against task definition"""
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), script_config["schema_files"][action])
    with open(schema_path) as fh:
        schema = json.load(fh)

    try:
        jsonschema.validate(task_definition, schema)
    except jsonschema.exceptions.ValidationError as exc:
        log.critical("Can't validate schema!\n{}".format(exc))
        sys.exit(3)


def get_task_behavior(task, script_config):
    """Extract task behavior from payload, fallback on scopes"""
    behavior = task.get("payload", {}).get("behavior")
    # Using scopes for which behavior (action) is deprecated in favor of explicit action in payload
    behaviors = {s.split(":")[-1] for s in task["scopes"] if s.startswith(script_config["taskcluster_scope_prefix"] + "action:")}
    if behavior:
        behaviors.add(behavior)
    if behaviors:
        log.info("actions: %s", behaviors)
        if len(behaviors) != 1:
            raise ValueError("Only one behavior can be used")
        behavior = behaviors.pop()
    else:
        behavior = "submit-locale"

    if behavior not in VALID_ACTIONS:
        raise ValueError("Invalid behavior")

    return behavior


def get_task_server(task, script_config):
    """Extract task server from scopes"""
    servers = [s.split(":")[-1] for s in task["scopes"] if s.startswith(script_config["taskcluster_scope_prefix"] + "server:")]
    log.info("Servers: %s", servers)
    if len(servers) != 1:
        raise ValueError("Only one server can be used")

    server = servers[0]
    if re.search("^[0-9A-Za-z_-]+$", server) is None:
        raise ValueError("Server {} is malformed".format(server))

    if server not in script_config["server_config"]:
        raise ValueError("Invalid server scope")

    return server


def get_manifest(script_config, upstream_artifacts):
    # assumes a single upstreamArtifact and single path
    task_id = upstream_artifacts[0]["taskId"]
    # FIXME: once we get rid of balrog_props.json, we should wipe the hardcode
    path = os.path.join(script_config["work_dir"], "cot", task_id, upstream_artifacts[0]["paths"][0])
    log.info("Reading manifest file %s" % path)
    try:
        with open(path, "r") as fh:
            manifest = json.load(fh)
    except (ValueError, OSError, IOError) as e:
        log.critical("Can't load manifest from {}!\n{}".format(path, e))
        sys.exit(3)
    return manifest


def get_upstream_artifacts(task):
    """Extract the upstream artifacts dictionaryt information"""
    return task["payload"]["upstreamArtifacts"]
