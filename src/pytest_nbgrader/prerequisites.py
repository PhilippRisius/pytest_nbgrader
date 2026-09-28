"""
Module for testing prerequisites a student's submission needs to fulfill.

Export functions for asserting properties of student code:
- has_signature -- is a function compatible with the supplied signature?

Might in the future test for static attributes or methods of classes
"""

from __future__ import annotations


__version__ = "0.3"

__all__ = ["has_signature", "writes", "writes_file"]

import contextlib
import importlib.util
import inspect
import io
import logging
import os
import pathlib
import sys
from collections.abc import Callable, Sequence
from typing import Any
from unittest import mock

import pytest

from pytest_nbgrader.cases import registered_module


logger = logging.getLogger(__name__)


def _execute_module(spec: importlib.machinery.ModuleSpec, name: str | None, argv: Sequence[str]) -> object:
    """
    Execute a fresh copy of the module described by ``spec``, like ``python <module> *argv``.

    The shared ``spec`` (usually the stored submission) is left untouched.

    Parameters
    ----------
    spec : importlib.machinery.ModuleSpec
        Module specification to be executed.
    name : str or None
        ``__name__`` of module at execution time; ``spec.name`` if None.
    argv : sequence of str
        Command line arguments seen by the module in ``sys.argv[1:]``.

    Returns
    -------
    object
        The ``sys.exit`` status if the module called it, otherwise None.
    """
    run_spec = importlib.util.spec_from_file_location(name or spec.name, spec.origin)
    module = importlib.util.module_from_spec(run_spec)
    with registered_module(module), mock.patch.object(sys, "argv", [str(spec.origin), *argv]):
        try:
            run_spec.loader.exec_module(module)
        except SystemExit as exit_:
            return exit_.code
    return None


def _snapshot(root: str = ".") -> dict[pathlib.Path, tuple[int, int]]:
    """
    Record size and modification time of all files below ``root``.

    Symlinks are not followed and ``__pycache__`` directories (written by the import system) are skipped.

    Parameters
    ----------
    root : str, optional
        Directory to walk, by default the current working directory.

    Returns
    -------
    dict
        Mapping of relative file paths to ``(size, mtime_ns)``.
    """
    snapshot = {}
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = [subdirectory for subdirectory in subdirectories if subdirectory != "__pycache__"]
        for filename in filenames:
            path = pathlib.Path(directory, filename)
            with contextlib.suppress(OSError):  # e.g. removed while walking
                stat = path.lstat()
                snapshot[path] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def writes_file(
    spec: importlib.machinery.ModuleSpec,
    *args: object,
    name: str | None = None,
    created: set[pathlib.Path] | None = None,
    deleted: set[pathlib.Path] | None = None,
    modified: set[pathlib.Path] | None = None,
    argv: Sequence[str] = (),
) -> pytest.ExitCode | tuple[pytest.ExitCode, Any, Any]:
    """
    Test file writes of module execution as ``name``.

    Parameters
    ----------
    spec : importlib.machinery.ModuleSpec
        Module specification to be executed.
    *args : tuple
        Unused positional arguments.
    name : str or None, optional
        ``__name__`` of module at execution time, by default None.
    created : set or None, optional
        Expected set of created file paths (relative to the working directory), by default None.
    deleted : set or None, optional
        Expected set of deleted file paths, by default None.
    modified : set or None, optional
        Expected set of modified file paths, by default None.
    argv : sequence of str, optional
        Command line arguments passed to the module, by default none.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if file operations match expectations,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None

    pre_exec_stats = _snapshot()
    exit_code = _execute_module(spec, name, argv)
    post_exec_stats = _snapshot()

    if exit_code not in (None, 0):
        logger.warning("Test failed: module %s exited with status %r.", spec.name, exit_code)
        result = (pytest.ExitCode.TESTS_FAILED, "exit status 0", exit_code)

    pre, post = set(pre_exec_stats.keys()), set(post_exec_stats.keys())
    created_files, deleted_files, shared_files = (
        post - pre,
        pre - post,
        pre & post,
    )
    modified_files = {file for file in shared_files if pre_exec_stats[file] != post_exec_stats[file]}

    for mode, expected, actual in [
        ("created", created, created_files),
        ("deleted", deleted, deleted_files),
        ("modified", modified, modified_files),
    ]:
        if expected is not None:
            expected = {pathlib.Path(path) for path in expected}
            if expected != actual:
                logger.warning(
                    "Test failed: module %s files (%s), but expected this exactly for files (%s)!",
                    mode,
                    ", ".join(map(str, actual)),
                    ", ".join(map(str, expected)),
                )
                result = (pytest.ExitCode.TESTS_FAILED, expected, actual)
            else:
                logger.debug("Test passed: module %s files %s as expected.", mode, expected)

    return result or pytest.ExitCode.OK


def writes(
    spec: importlib.machinery.ModuleSpec,
    *args: object,
    name: str | None = None,
    out: str | None = None,
    err: str | None = None,
    argv: Sequence[str] = (),
    **kwargs: object,
) -> pytest.ExitCode:
    """
    Test stdout and stderr writes of module execution as ``name``.

    Parameters
    ----------
    spec : importlib.machinery.ModuleSpec
        Module specification to be executed.
    *args : tuple
        Unused positional arguments.
    name : str or None, optional
        ``__name__`` of module at execution time, by default None.
    out : str or None, optional
        Expected stdout output, skipped if None.
    err : str or None, optional
        Expected stderr output, skipped if None.
    argv : sequence of str, optional
        Command line arguments passed to the module, by default none.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if stdout/stderr match expectations,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """

    def message(name: str, output: str, actual: str, expected: str) -> str:
        """
        Format message for warning.

        Parameters
        ----------
        name : str
            Module name.
        output : str
            Output stream name (stdout or stderr).
        actual : str
            Actual output written.
        expected : str
            Expected output.

        Returns
        -------
        str
            Formatted warning message.
        """
        return (
            f"Importing the module {name} wrote"
            f" {repr(actual) if actual else 'nothing'} to {output},"
            f" expected {repr(expected) if expected else 'nothing'}"
        )

    result = None

    outputs = {
        contextlib.redirect_stdout: ("stdout", out, io.StringIO()),
        contextlib.redirect_stderr: ("stderr", err, io.StringIO()),
    }

    with contextlib.ExitStack() as stack:
        for redirect, (_output, expected, target) in outputs.items():
            if expected is not None:
                stack.enter_context(redirect(target))
        exit_code = _execute_module(spec, name, argv)

    if exit_code not in (None, 0):
        logger.warning("Module %s exited with status %r.", spec.name, exit_code)
        result = pytest.ExitCode.TESTS_FAILED

    for output, expected, actual in outputs.values():
        if expected is None:
            continue
        actual = actual.getvalue()
        if actual != expected:
            logger.warning(message(spec.name, output, actual, expected))
            result = pytest.ExitCode.TESTS_FAILED
        else:
            logger.debug(message(spec.name, output, actual, expected))

    return result or pytest.ExitCode.OK


def has_signature(
    function: Callable[..., Any],
    ref_sig: inspect.Signature,
    *strict_comparisons: str,
    compare_names: Callable[[list[str], list[str]], bool] = list.__eq__,
    **comparisons: Callable[[Any, Any], bool],
) -> pytest.ExitCode:
    """
    Test if function is compatible with passed signature.

    Parameters
    ----------
    function : callable
        The function whose signature is to be tested.
    ref_sig : inspect.Signature
        Reference signature to compare against.
    *strict_comparisons : str
        Parameter attributes to compare using strict equality.
    compare_names : callable, optional
        Function to compare parameter name lists, by default ``list.__eq__``.
    **comparisons : callable
        Mapping of parameter attributes to comparison functions.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if signature matches,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """

    def invalid_signature(expected: object, actual: object) -> str:
        """
        Format message for warnings.

        Parameters
        ----------
        expected : object
            Expected signature or parameter.
        actual : object
            Actual signature or parameter.

        Returns
        -------
        str
            Formatted warning message.
        """
        return f"Function signature is not valid.\n{expected = },\n  {actual = }."

    def pretty_par(par: inspect.Parameter) -> str:
        """
        Pretty formatting of function parameters.

        Parameters
        ----------
        par : inspect.Parameter
            The parameter to format.

        Returns
        -------
        str
            Human-readable parameter description.
        """
        string = f"{par.kind.name} parameter <{par.name}"
        if par.annotation is not inspect.Parameter.empty:
            string += f": {par.annotation}"
        if par.default is not inspect.Parameter.empty:
            string += f" = {par.default}"
        string += ">"
        return string

    try:
        fun_sig = inspect.signature(function, eval_str=True)
    except Exception:  # noqa: BLE001 - annotations that cannot be evaluated are compared as strings
        fun_sig = inspect.signature(function)
    result = None

    if not compare_names(list(fun_sig.parameters), list(ref_sig.parameters)):
        logger.warning(invalid_signature(list(ref_sig.parameters), list(fun_sig.parameters)))
        result = pytest.ExitCode.TESTS_FAILED

    for name, fun_par in fun_sig.parameters.items():
        ref_par = ref_sig.parameters.get(name)
        if ref_par is not None:
            for attr in strict_comparisons:
                comparisons[attr] = type(getattr(fun_par, attr)).__eq__
            for attr, comp in comparisons.items():
                fun_value, ref_value = getattr(fun_par, attr), getattr(ref_par, attr)
                if comp(fun_value, ref_value) is not True:
                    logger.warning(invalid_signature(pretty_par(ref_par), pretty_par(fun_par)))
                    result = pytest.ExitCode.TESTS_FAILED

    ref_return, fun_return = ref_sig.return_annotation, fun_sig.return_annotation
    if "annotation" in strict_comparisons:
        comparisons["annotation"] = type(fun_return).__eq__
    if "annotation" in comparisons:
        # same argument order as for parameters: (submission, reference)
        if comparisons["annotation"](fun_return, ref_return) is not True:
            logger.warning("Return annotation of %s", invalid_signature(ref_return, fun_return))
            result = pytest.ExitCode.TESTS_FAILED

    return result or pytest.ExitCode.OK
