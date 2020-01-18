#!/usr/bin/env python
"""Mock xcrun for integration testing without an Apple dependency.

It's fairly easy to test ``notarization_poller`` for behavior around a single
task. It's trickier to determine whether it behaves correctly around
multiple concurrent tasks. This tool allows for running multiple concurrent
tasks on ``notarization_poller``, so we can determine whether the task results
match expectations.

There are four types of results we can get from running ``xcrun altool``:

- exit code 0, ``Status: pending`` in output. This means Apple knows
  about the UUID, but notarization is still pending. This result means
  we should keep polling.
- exit code 0, ``Status: success`` in output. This means notarization
  is done and ready to staple; we should stop polling this UUID.
- exit code 0, ``Status: invalid`` in output. This means notarization
  failed for some reason, and we need to re-submit the notarization
  request. We should stop polling this UUID, and fail this task.
- non-zero exit code. This could be a sign that Apple's service is
  down or severely backed up. ``notarization_poller`` will retry this
  ``n`` times, and then exit with ``intermittent-task`` if we run out of
  retry attempts.

  This can be further split into

    - non-zero exit code for ``n`` attempts, where ``n`` is less than our
      max retries, but then result in one of the first 3 statuses, or
    - non-zero exit code for ``n`` attempts, where ``n`` is greater than
      our max retries,  which results in ``intermittent-task``.

We want this tool to be a) deterministic, so we can declaratively say what
we want the results for each UUID for each task is at task creation time,
b) timed, so we can test for varying turnaround speeds and upstream
bustage, and c) simple.

Because xcrun is run as a commandline tool, potentially multiple times for
each UUID, with potentially multiple UUIDs per task, we either need to
maintain a history of queries (e.g., we want a ``Status: success`` on the
3rd poll of this UUID; the standalone tool would need to know it had been
run 2 times before somehow), or we need an alternate solution. This could
be a timestamp or an offset from claim time. For now, we're going with
history.

Because we need a clean ``.notarization_cache`` directory per integration run,
and because we want to clean these up afterwards, it may make sense to copy
this script into a temp directory per integration run.

Attributes:
    HISTORY_DIR (str): the path to the directory holding UUID information.

"""

import argparse
import os
import sys
import time

HISTORY_DIR = os.path.join(os.path.dirname(__file__), ".notarization_cache")


def parse_args(args):
    """Parse cmdln args."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--notarization-info", type=str)
    parsed_args, _ = parser.parse_known_args(args)
    return parsed_args


def main():
    """Main function."""
    args = sys.argv[1:]
    parsed_args = parse_args(args)
    uuid = parsed_args.notarization_info
    print(uuid)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    # XXX add sleep to mimic response turnaround time from Apple?
    # determine uuid behavior
    # find any uuid polling history in HISTORY_DIR, if applicable
    # write new polling history
    # output any required output for this run, exit appropriately


__name__ == "__main__" and main()
