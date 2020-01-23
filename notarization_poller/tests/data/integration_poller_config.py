#!/usr/bin/env python

import os
from copy import deepcopy

import slugid

from aiohttp import ClientSession
from notarization_poller.constants import DEFAULT_CONFIG
from taskcluster.aio import Queue


def build_config(override, basedir):
    randstring = slugid.nice().lower().replace("_", "").replace("-", "")[:6]
    config = deepcopy(DEFAULT_CONFIG)
    config.update(
        {
            "taskcluster_access_token": os.environ.get("TASKCLUSTER_ACCESS_TOKEN"),
            "taskcluster_client_id": os.environ.get("TASKCLUSTER_CLIENT_ID"),
            "provisioner_id": "test-dummy-provisioner",
            "worker_group": "test-dummy-workers",
            "worker_type": "dummy-worker-{}".format(randstring),
            "worker_id": "dummy-worker-{}".format(randstring),
            "notarization_username": "fakeuser",
            "notarization_password": "fakepass",
            "xcrun_cmd": (os.path.join(basedir, "fake_xcrun.py"),),
            "verbose": True,
        }
    )
    if isinstance(override, dict):
        config.update(override)
    return config


async def integration_test():
    pass
