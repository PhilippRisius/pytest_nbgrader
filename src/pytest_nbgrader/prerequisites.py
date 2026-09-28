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

    Directories are walked in sorted order. Symlinks to directories outside ``root`` are followed
    (each such directory once, so link loops are harmless); symlinks to directories inside ``root``
    are not, because those are walked through their real path. ``__pycache__`` directories,
    written by the import system, are skipped.

    Parameters
    ----------
    root : str, optional
        Directory to walk, by default the current working directory.

    Returns
    -------
    dict
        Mapping of relative file paths to ``(size, mtime_ns)``.
    """
    real_root = pathlib.Path(root).resolve()
    snapshot = {}
    visited = set()
    for directory, subdirectories, filenames in os.walk(root, followlinks=True):
        directory_stat = pathlib.Path(directory).stat()
        if (directory_stat.st_dev, directory_stat.st_ino) in visited:
            subdirectories.clear()
            continue
        visited.add((directory_stat.st_dev, directory_stat.st_ino))
        subdirectories[:] = sorted(
            subdirectory
            for subdirectory in subdirectories
            if subdirectory != "__pycache__" and not _links_inside(pathlib.Path(directory, subdirectory), real_root)
        )
        for filename in filenames:
            path = pathlib.Path(directory, filename)
            with contextlib.suppress(OSError):  # e.g. removed while walking
                # a dangling symlink has no target to stat
                stat = path.stat() if path.exists() else path.lstat()
                snapshot[path] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def _links_inside(path: pathlib.Path, root: pathlib.Path) -> bool:
    """
    Tell whether ``path`` is a symlink to a directory inside ``root``.

    Parameters
    ----------
    path : pathlib.Path
        Path to check.
    root : pathlib.Path
        Resolved root directory.

    Returns
    -------
    bool
        True for a symlink whose target lies inside ``root``.
    """
    try:
        return path.is_symlink() and path.resolve().is_relative_to(root)
    except OSError:  # e.g. inside a directory that can be listed but not entered; os.walk skips it
        return False


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


def _invalid_signature(expected: object, actual: object) -> str:
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


def _pretty_par(par: inspect.Parameter) -> str:
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


def _signature_mismatches(
    fun_sig: inspect.Signature,
    ref_sig: inspect.Signature,
    strict_comparisons: tuple[str, ...],
    compare_names: Callable[[list[str], list[str]], bool],
    comparisons: dict[str, Callable[[Any, Any], bool]],
) -> list[str]:
    """
    Compare a signature of the tested function with the reference signature.

    Parameters
    ----------
    fun_sig : inspect.Signature
        Signature of the tested function.
    ref_sig : inspect.Signature
        Reference signature.
    strict_comparisons : tuple of str
        Parameter attributes to compare using strict equality.
    compare_names : callable
        Function to compare parameter name lists.
    comparisons : dict
        Mapping of parameter attributes to comparison functions.

    Returns
    -------
    list of str
        Descriptions of all differences.
    """
    problems = []
    comps = dict(comparisons)

    if not compare_names(list(fun_sig.parameters), list(ref_sig.parameters)):
        problems.append(_invalid_signature(list(ref_sig.parameters), list(fun_sig.parameters)))

    for name, fun_par in fun_sig.parameters.items():
        ref_par = ref_sig.parameters.get(name)
        if ref_par is not None:
            for attr in strict_comparisons:
                comps[attr] = type(getattr(fun_par, attr)).__eq__
            for attr, comp in comps.items():
                fun_value, ref_value = getattr(fun_par, attr), getattr(ref_par, attr)
                if comp(fun_value, ref_value) is not True:
                    problems.append(_invalid_signature(_pretty_par(ref_par), _pretty_par(fun_par)))

    ref_return, fun_return = ref_sig.return_annotation, fun_sig.return_annotation
    if "annotation" in strict_comparisons:
        comps["annotation"] = type(fun_return).__eq__
    # same argument order as for parameters: (submission, reference)
    if "annotation" in comps and comps["annotation"](fun_return, ref_return) is not True:
        problems.append(f"Return annotation of {_invalid_signature(ref_return, fun_return)}")

    return problems


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

    def mismatches(fun_sig: inspect.Signature) -> list[str]:
        """
        Compare a signature with the reference; a comparison that raises counts as a mismatch.

        Parameters
        ----------
        fun_sig : inspect.Signature
            Signature of the tested function.

        Returns
        -------
        list of str
            Descriptions of all differences.
        """
        try:
            return _signature_mismatches(fun_sig, ref_sig, strict_comparisons, compare_names, comparisons)
        except Exception as e:  # noqa: BLE001 - e.g. a custom comparator that cannot handle string annotations
            return [f"Comparing the signature raised {e!r}"]

    raw_sig = inspect.signature(function)
    problems = mismatches(raw_sig)
    if problems:
        # Postponed (string) annotations: the reference may hold the evaluated types instead.
        try:
            evaluated_sig = inspect.signature(function, eval_str=True)
        except Exception:  # noqa: BLE001 - annotations that cannot be evaluated stay strings
            evaluated_sig = raw_sig
        if evaluated_sig != raw_sig and not mismatches(evaluated_sig):
            problems = []

    for problem in problems:
        logger.warning(problem)
    return pytest.ExitCode.TESTS_FAILED if problems else pytest.ExitCode.OK
