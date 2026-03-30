"""
Module for testing prerequisites a student's submission needs to fulfill.

Export functions for asserting properties of student code:
- has_signature -- is a function compatible with the supplied signature?

Might in the future test for static attributes or methods of classes
"""

__version__ = "0.3"

import importlib.util
import inspect
import io
import logging
from enum import Enum

import pytest


logger = logging.getLogger()


def writes_file(spec, *args, name=None, created=None, deleted=None, modified=None) -> Enum:
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
        Expected set of created file paths, by default None.
    deleted : set or None, optional
        Expected set of deleted file paths, by default None.
    modified : set or None, optional
        Expected set of modified file paths, by default None.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if file operations match expectations,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    import pathlib

    def recursive_stats(path: pathlib.Path, return_dict=None):
        """
        Recursively gather file paths and stats in subdirs.

        Parameters
        ----------
        path : pathlib.Path
            Root path to start gathering stats from.
        return_dict : dict or None, optional
            Accumulator dict for recursive calls, by default None.

        Returns
        -------
        dict
            Mapping of file paths to their stat results.
        """
        if return_dict is None:
            return_dict = {}
        if path.is_file():
            return_dict[path] = path.stat()
        else:
            for child in path.iterdir():
                return_dict = recursive_stats(child, return_dict)
        return return_dict

    result = None

    module = importlib.util.module_from_spec(spec)

    if name is not None:
        logger.debug("changing name to %s", name)
        spec_name, spec.name = spec.name, name
        spec_loader_name, spec.loader.name = spec.loader.name, name
        module.__name__ = name

    pre_exec_stats = recursive_stats(pathlib.Path())
    spec.loader.exec_module(module)
    post_exec_stats = recursive_stats(pathlib.Path())

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

    if name is not None:
        spec.name, spec.loader.name = spec_name, spec_loader_name

    return result or pytest.ExitCode.OK


def writes(spec, *args, name=None, out=None, err=None, **kwargs) -> Enum:
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
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if stdout/stderr match expectations,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    from contextlib import ExitStack, redirect_stderr, redirect_stdout

    def message(name, output, actual, expected):
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

    module = importlib.util.module_from_spec(spec)

    if name is not None:
        spec_name, spec.name = spec.name, name
        spec_loader_name, spec.loader.name = spec.loader.name, name
        module.__name__ = name

    outputs = {
        redirect_stdout: ("stdout", out, io.StringIO()),
        redirect_stderr: ("stderr", err, io.StringIO()),
    }

    with ExitStack() as stack:
        for redirect, (_output, expected, target) in outputs.items():
            if expected is not None:
                stack.enter_context(redirect(target))
        spec.loader.exec_module(module)

    for output, expected, actual in outputs.values():
        if expected is None:
            continue
        actual = actual.getvalue()
        if actual != expected:
            logging.warning(message(spec.name, output, actual, expected))
            result = pytest.ExitCode.TESTS_FAILED
        else:
            logging.debug(message(spec.name, output, actual, expected))

    if name is not None:
        spec.name, spec.loader.name = spec_name, spec_loader_name

    return result or pytest.ExitCode.OK


def has_signature(
    function: callable,
    ref_sig: inspect.Signature,
    *strict_comparisons,
    compare_names: callable = list.__eq__,
    **comparisons,
):
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

    def invalid_signature(expected, actual):
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

    if "annotation" in strict_comparisons:
        comparisons["annotation"] = type(ref_sig.return_annotation).__eq__
    if "annotation" in comparisons:
        ref_return, fun_return = (
            ref_sig.return_annotation,
            fun_sig.return_annotation,
        )
        if comparisons["annotation"](ref_return, fun_return) is not True:
            logger.warning("Return annotation of %s", invalid_signature(ref_return, fun_return))
            result = pytest.ExitCode.TESTS_FAILED

    return result or pytest.ExitCode.OK
