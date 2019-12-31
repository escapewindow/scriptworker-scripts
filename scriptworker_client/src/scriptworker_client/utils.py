#!/usr/bin/env python
"""Generic utils for scriptworker-client.

Attributes:
    log (logging.Logger): the log object for the module

"""
import asyncio
import json
import logging
import os
import shutil
import tempfile
from asyncio.subprocess import PIPE
from contextlib import contextmanager

import yaml

from scriptworker_client.exceptions import TaskError

log = logging.getLogger(__name__)


# load_json_or_yaml {{{1
def load_json_or_yaml(
    string,
    is_path=False,
    file_type="json",
    exception=TaskError,
    message="Failed to load %(file_type)s: %(exc)s",
):
    """Load json or yaml from a filehandle or string, and raise a custom exception on failure.

    Args:
        string (str): json/yaml body or a path to open
        is_path (bool, optional): if ``string`` is a path. Defaults to False.
        file_type (str, optional): either "json" or "yaml". Defaults to "json".
        exception (exception, optional): the exception to raise on failure.
            If None, don't raise an exception.  Defaults to TaskError.
        message (str, optional): the message to use for the exception.
            Defaults to "Failed to load %(file_type)s: %(exc)s"

    Returns:
        dict: the data from the string.

    Raises:
        Exception: as specified, on failure

    """
    if file_type == "json":
        _load_fh = json.load
        _load_str = json.loads
    else:
        _load_fh = yaml.safe_load
        _load_str = yaml.safe_load

    try:
        if is_path:
            with open(string, "r") as fh:
                contents = _load_fh(fh)
        else:
            contents = _load_str(string)
        return contents
    except (OSError, ValueError, yaml.scanner.ScannerError) as exc:
        if exception is not None:
            repl_dict = {"exc": str(exc), "file_type": file_type}
            raise exception(message % repl_dict) from exc


# get_artifact_path {{{1
def get_artifact_path(task_id, path, work_dir=None):
    """Get the path to an artifact.

    Args:
        task_id (str): the ``taskId`` from ``upstreamArtifacts``
        path (str): the ``path`` from ``upstreamArtifacts``
        work_dir (str, optional): the *script ``work_dir``. If ``None``,
            return a relative path. Defaults to ``None``.

    Returns:
        str: the path to the artifact.

    """
    if work_dir is not None:
        base_dir = os.path.join(work_dir, "cot")
    else:
        base_dir = "cot"
    return os.path.join(base_dir, task_id, path)


# to_unicode {{{1
def to_unicode(line):
    """Avoid ``b'line'`` type messages in the logs.

    Lifted from ``scriptworker.utils.to_unicode``.

    Args:
        line (str): The bytecode or unicode string.

    Returns:
        str: the unicode-decoded string, if ``line`` was a bytecode string.
            Otherwise return ``line`` unmodified.

    """
    try:
        line = line.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        pass
    return line


# pipe_to_log {{{1
async def pipe_to_log(pipe, filehandles=(), level=logging.INFO):
    """Log from a subprocess PIPE.

    Lifted from ``scriptworker.log.pipe_to_log``

    Args:
        pipe (filehandle): subprocess process STDOUT or STDERR
        filehandles (list of filehandles, optional): the filehandle(s) to write
            to.  If empty, don't write to a separate file.  Defaults to ().
        level (int, optional): the level to log to.  Defaults to ``logging.INFO``.

    """
    while True:
        line = await pipe.readline()
        if line:
            line = to_unicode(line)
            log.log(level, line.rstrip())
            for filehandle in filehandles:
                print(line, file=filehandle, end="")
        else:
            break


# get_log_filehandle {{{1
@contextmanager
def get_log_filehandle(log_path=None):
    """Open a log filehandle.

    Args:
        log_path (str, optional): the path to log to. If ``None``, create
            a temp file to log to, and delete once we exit the context.
            Defaults to ``None``.

    """
    if log_path is not None:
        with open(log_path, "w+") as log_filehandle:
            yield log_filehandle
    else:
        with tempfile.TemporaryFile(mode="w+") as log_filehandle:
            yield log_filehandle


# run_command {{{1
async def run_command(
    cmd,
    log_path=None,
    log_cmd=None,
    log_level=logging.INFO,
    cwd=None,
    env=None,
    exception=None,
    expected_exit_codes=(0,),
    output_log_on_exception=False,
):
    """Run a command using ``asyncio.create_subprocess_exec``.

    This logs to `log_path` and returns the exit code.

    Largely lifted from ``scriptworker.task.run_task``

    We can add a bunch more bells and whistles (timeout, logging options, etc)
    but let's add those when needed, rather than guessing what we'll need.

    Args:
        cmd (list): the command to run.
        log_path (str, optional): the path to the file to write output to.
            This file will be overwritten. The directory should already exist.
            If ``None``, create a temp file to log to that will be deleted
            after the command is complete. Defaults to ``None``.
        log_cmd (str, optional): the command to log. Set this if there is
            sensitive information in ``cmd``. If ``None``, defaults to ``cmd``.
            Defaults to ``None``.
        log_level (int, optional): the level to log the command output.
            Defaults to ``logging.INFO``.
        cwd (str, optional): the directory to run the command in. If ``None``,
            use ``os.getcwd()``. Defaults to ``None``.
        exception (Exception, optional): the exception to raise if the exit
            code isn't in ``expected_exit_codes``. If ``None``, don't raise.
            Defaults to ``None``.
        expected_exit_codes (list, optional): the list of exit codes for
            a successful run. Only used if ``exception`` is not ``None``.
            Defaults to ``(0, )``.
        output_log_on_exception (bool, optional): log the output log if we're
            raising an exception.

    Returns:
        int: the exit code of the command

    """
    cwd = cwd or os.getcwd()
    log_cmd = log_cmd or cmd
    log.info("Running {} in {} ...".format(log_cmd, cwd))

    kwargs = {
        "stdout": PIPE,
        "stderr": PIPE,
        "stdin": None,
        "close_fds": True,
        "preexec_fn": os.setsid,
        "cwd": cwd,
    }
    if env is not None:
        kwargs["env"] = env
    proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
    with get_log_filehandle(log_path=log_path) as log_filehandle:
        stderr_future = asyncio.ensure_future(
            pipe_to_log(proc.stderr, filehandles=[log_filehandle], level=log_level)
        )
        stdout_future = asyncio.ensure_future(
            pipe_to_log(proc.stdout, filehandles=[log_filehandle], level=log_level)
        )
        _, pending = await asyncio.wait([stderr_future, stdout_future])
        exitcode = await proc.wait()
        await asyncio.wait([stdout_future, stderr_future])
        if exception and exitcode not in expected_exit_codes:
            log_contents = ""
            if output_log_on_exception:
                log_filehandle.seek(0)
                log_contents = log_filehandle.read()
            raise exception(
                "%s in %s exited %s!\n%s", log_cmd, cwd, exitcode, log_contents
            )
    log.info("%s in %s exited %d", log_cmd, cwd, exitcode)
    return exitcode


# list_files {{{1
def list_files(path, ignore_list=None):
    """Recursively list the files in a directory.

    This currently treats softlinks as files, even if they're pointing to
    directories.

    Args:
        path (str): the top directory
        ignore_list (list): the directory or file names to ignore. If ``None``,
            use ``('.', '..')``. Defaults to ``None``.

    Yields:
        iterable: the paths to the files

    """
    if ignore_list is None:
        ignore_list = (".", "..")
    with os.scandir(path) as it:
        for entry in it:
            if entry.name in ignore_list:
                continue
            if entry.is_dir():
                for file_ in list_files(
                    os.path.join(path, entry.name), ignore_list=ignore_list
                ):
                    yield file_
            else:
                yield os.path.join(path, entry.name)


# makedirs {{{1
def makedirs(path):
    """Equivalent to mkdir -p.

    Args:
        path (str): the path to mkdir -p

    Raises:
        TaskError: if path exists already and the realpath is not a dir.

    """
    if path:
        try:
            log.debug("makedirs({})".format(path))
            realpath = os.path.realpath(path)
            os.makedirs(realpath, exist_ok=True)
        except OSError as e:
            raise TaskError("makedirs: error creating {}: {}".format(path, e)) from e


# rm {{{1
def rm(path):
    """Equivalent to rm -rf.

    Make sure ``path`` doesn't exist after this call.  If it's a dir,
    shutil.rmtree(); if it's a file, os.remove(); if it doesn't exist,
    ignore.

    Args:
        path (str): the path to nuke.

    """
    if path and os.path.exists(path):
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
