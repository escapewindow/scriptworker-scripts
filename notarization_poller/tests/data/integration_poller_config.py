#!/usr/bin/env python

import os
import shutil
from copy import deepcopy

import slugid

from aiohttp import ClientSession
from notarization_poller.constants import DEFAULT_CONFIG
from taskcluster.aio import Queue

FAKE_XCRUN = os.path.join(os.path.dirname(__file__), "data", "fake_xcrun.py")


def integration_credentials():
    # TODO support to read from local files?
    return {
        "taskcluster_access_token": os.environ.get("TASKCLUSTER_ACCESS_TOKEN"),
        "taskcluster_client_id": os.environ.get("TASKCLUSTER_CLIENT_ID"),
    }

def build_config(override, basedir):
    randstring = slugid.nice().lower().replace("_", "").replace("-", "")[:6]
    config = deepcopy(DEFAULT_CONFIG)
    config.update(
        {
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
    config.update(integration_credentials())
    if isinstance(override, dict):
        config.update(override)
    with open(os.path.join(basedir, "poller.yaml") as fh:
        yaml.safe_dump(config, stream=fh)
    return config


@pytest.fixture(scope="function")
def base_work_dir(tmpdir):
    orig_dir = os.getcwd()
    shutil.copyfile(FAKE_XCRUN, os.path.join(str(tmpdir), "fake_xcrun.py"))
    config = build_config({}, str(tmpdir))
    os.chdir(str(tmpdir))
    for i in ("log_dir", "work_dir"):
        os.makedirs(config[i])
    yield tmpdir
    os.chdir(orig_dir)


async def integration_test():
    pass
