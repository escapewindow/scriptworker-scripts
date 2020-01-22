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

"""

import argparse
import os
import sys


def get_uuid_behavior(uuid, hist_len):
    """Decode the UUID for expected behaviors.

    The UUID can have the following characters:

    - p: exit 0, status pending
    - s: exit 0, status success
    - i: exit 0, status invalid
    - e: exit non-zero (default)

    Args:
        uuid (str): the uuid to parse
        hist_len (int): the length of historical behaviors, which should
            map to the array index

    Returns:
        list: the list of behaviors

    """
    try:
        behavior = uuid[hist_len]
    except IndexError:
        behavior = "e"
    return behavior


def get_uuid_history(history_dir, uuid):
    """Parse the history file to determine the next behavior.

    Args:
        history_dir (str): the directory to parse
        uuid (str): the uuid to parse

    Returns:
        int: the number of previous actions

    """
    try:
        with open(os.path.join(history_dir, uuid)) as fh:
            return len(fh.readlines())
    except OSError:
        return 0


def append_behavior(history_dir, uuid, behavior):
    """Append the behavior to the history file.

    Args:
        history_dir (str): the directory to parse
        uuid (str): the uuid to parse
        behavior (str): the behavior to perform.

    """
    with open(os.path.join(history_dir, uuid), "a") as fh:
        print(behavior, file=fh)


def do_behavior(behavior):
    """Perform the behavior.

    Args:
        behavior (str): the behavior to perform.

    """
    exit_val = 0
    if behavior == "p":
        print("Status: pending")
    elif behavior == "s":
        print("Status: success")
    elif behavior == "i":
        print("Status: invalid")
    else:
        print("Unexpected error")
        exit_val = 2

    sys.exit(exit_val)


def parse_args(args):
    """Parse cmdln args, ignoring unknown options.

    Args:
        args (list): the list of cmdln args (``sys.argv[1:]``)

    Returns:
        ``argparse.Namespace``: the parsed args

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--notarization-info", type=str)
    parser.add_argument("--history-dir", type=str, default=os.path.join(os.path.dirname(__file__), ".notarization_cache"))
    parsed_args, _ = parser.parse_known_args(args)
    return parsed_args


def main():
    """Main function."""
    args = sys.argv[1:]
    parsed_args = parse_args(args)
    uuid = parsed_args.notarization_info or "e"
    history_dir = parsed_args.history_dir
    print(uuid)
    os.makedirs(history_dir, exist_ok=True)
    # XXX add sleep to mimic response turnaround time from Apple?
    hist_len = get_uuid_history(history_dir, uuid)
    behavior = get_uuid_behavior(uuid, hist_len)
    append_behavior(history_dir, uuid, behavior)
    do_behavior(behavior)


__name__ == "__main__" and main()
