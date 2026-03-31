"""
Module for testing actual and expected outputs of a TestCase.

Export functions for asserting relations between student outputs and expected outputs:
- close_attributes --
- equal_attributes --
- has_import --
- has_method --
- calls --
- equal_contents -- Do output containers have contents exactly as expected?
- almost_equal -- Are outputs almost equal to expected?
- equal_value -- Are outputs exactly equal to expected?
- equal_type -- Are output objects of expected types?
- equal_scope -- Is the output scope as expected (i.e. same variables present)?
"""

from __future__ import annotations


__version__ = "0.3"

__all__ = [
    "almost_equal",
    "calls",
    "close_attributes",
    "equal_attributes",
    "equal_contents",
    "equal_scope",
    "equal_types",
    "equal_value",
    "file_contents",
    "has_import",
    "has_method",
    "raises",
    "time_bounds",
]

import functools
import inspect
import logging
import pathlib
import types
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from pytest_nbgrader.cases import TestCase


_AssertionResult = pytest.ExitCode | tuple[pytest.ExitCode, Any, Any]

_SENTINEL = object()


def _log(
    assertion: Callable[..., _AssertionResult],
    name: str = "",
) -> Callable[..., tuple[pytest.ExitCode, str]]:
    """
    Log failures and successes of running assertions.

    Parameters
    ----------
    assertion : callable
        The assertion function to wrap with logging.
    name : str, optional
        Display name for log messages, by default uses ``assertion.__name__``.

    Returns
    -------
    callable
        Wrapped assertion function that logs results.
    """
    name = f'Assertion "{name or assertion.__name__}"'

    @functools.wraps(assertion)
    def wrapper(case: TestCase, outputs: object, *args: Any, **kwargs: Any) -> tuple[pytest.ExitCode, str]:
        """
        Append a message to the test result.

        Parameters
        ----------
        case : TestCase
            Test case with expected outputs.
        outputs : tuple
            Actual outputs from student submission.
        *args : tuple
            Positional arguments forwarded to the assertion.
        **kwargs : dict
            Keyword arguments forwarded to the assertion.

        Returns
        -------
        tuple
            A ``(result, message)`` pair.
        """
        result = assertion(case, outputs, *args, **kwargs)
        if result is pytest.ExitCode.OK:
            logging.debug("%s succeeded:\nExpected: %s\nActual: %s\n", name, case.expected, outputs)
            message = ""
        else:
            result, expect, actual = result
            message = f"{name} failed with result {result}.\nExpected: {expect},\nActual: {actual}.\n"

        return result, message

    return wrapper


@_log
def close_attributes(case: TestCase, outputs: object, *args: str, **kwargs: float) -> _AssertionResult:
    """
    Assert close values for given attributes between expected and outputs.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : object
        Actual output object whose attributes are compared.
    *args : str
        Attribute names to compare.
    **kwargs : dict
        Tolerances forwarded to ``np.testing.assert_allclose``.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` on success, or a failure tuple.
    """
    try:
        expected_attrs, output_attrs = ([getattr(instance, attribute) for attribute in args] for instance in (case.expected, outputs))
        np.testing.assert_allclose(expected_attrs, output_attrs, **kwargs)
        return pytest.ExitCode.OK
    except AssertionError:
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs


@_log
def has_import(case: TestCase, outputs: tuple, *args: pathlib.Path, **kwargs: pathlib.Path | None) -> _AssertionResult:
    """
    Test if an object has a module-level import.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs ``(positional, named, elapsed)`` from student submission.
        The return object is taken from ``outputs[0][0]``.
    *args : pathlib.Path
        Expected import paths to check (positional).
    **kwargs : pathlib.Path or None
        Mapping of object names to expected import paths (None = locally defined).

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all imports match, otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """

    def invalid_import(name: str, expected: object = None, actual: object = None) -> str:
        """
        Format message for warning about invalid imports.

        Parameters
        ----------
        name : str
            Name of the import.
        expected : str or None, optional
            Expected import location.
        actual : str or None, optional
            Actual import location.

        Returns
        -------
        str
            Formatted warning message.
        """
        message = f"{name} was not imported"
        if expected or actual:
            expected = expected or "locally defined"
            actual = actual or "locally defined"
            message += f" from expected location.\n expected: {expected}, actual: {actual}"
        return message + "."

    def _resolve_origin(module: types.ModuleType) -> pathlib.Path:
        """
        Return the origin path of a module, relative to cwd if possible.

        Parameters
        ----------
        module : types.ModuleType
            The module whose origin to resolve.

        Returns
        -------
        pathlib.Path
            The module's origin path, relative to cwd when possible.
        """
        origin = pathlib.Path(module.__spec__.origin)
        try:
            return origin.relative_to(pathlib.Path.cwd())
        except ValueError:
            return origin

    if not outputs[0]:
        return pytest.ExitCode.TESTS_FAILED, "expected object", "no return object"

    return_obj = outputs[0][0]
    result = None

    for expected in args:
        actual = inspect.getmodule(getattr(return_obj, expected))
        if actual is None:
            logging.warning(invalid_import(expected.stem, expected, "not imported"))
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected.stem,
                "not imported",
            )
        else:
            actual_origin = _resolve_origin(actual)
            if (expected.stem, expected) != (actual.__spec__.name, actual_origin):
                logging.warning(invalid_import(expected.stem, expected, actual_origin))
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    expected.stem,
                    actual.__spec__.name,
                )

    for obj, expected in kwargs.items():
        actual = inspect.getmodule(getattr(return_obj, obj))
        if actual is not None:
            actual_origin = _resolve_origin(actual)
            if expected is None:
                logging.warning(invalid_import(obj, None, actual_origin))
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    "locally defined",
                    actual_origin,
                )
            elif (expected.stem, expected) != (actual.__spec__.name, actual_origin):
                logging.warning(invalid_import(obj, expected, actual_origin))
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    expected,
                    actual_origin,
                )
            else:
                logging.debug('Test "%s imported from %s" succeeded.', obj, expected.stem)
        elif expected is not None:
            logging.warning(invalid_import(obj, expected, None))
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected,
                "not imported",
            )
        else:
            logging.debug('Test "%s was locally defined" succeeded.', obj)

    return result or pytest.ExitCode.OK


@_log
def equal_attributes(case: TestCase, outputs: tuple, *args: str, **kwargs: object) -> _AssertionResult:
    """
    Test if all attributes of expected and actual return object are equal.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs ``(positional, named, elapsed)`` from student submission.
        The return object is taken from ``outputs[0][0]``; the expected object
        from ``case.expected[0][0]``.
    *args : str
        Attribute names to compare.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if equal, otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    if not outputs[0]:
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs

    return_obj = outputs[0][0]
    expected_obj = case.expected[0][0]

    if not all(getattr(return_obj, attr, _SENTINEL) == getattr(expected_obj, attr, _SENTINEL) for attr in args):
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs

    return pytest.ExitCode.OK


@_log
def has_method(case: TestCase, outputs: tuple, *args: str, **kwargs: type) -> _AssertionResult:
    """
    Test if return object has given methods/attributes.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs ``(positional, named, elapsed)`` from student submission.
        The return object is taken from ``outputs[0][0]``.
    *args : str
        Attribute names that must exist on the return object.
    **kwargs : dict
        Mapping of attribute names to expected type hints.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all methods exist with correct types,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    if not outputs[0]:
        return pytest.ExitCode.TESTS_FAILED, args, "no return object"

    return_obj = outputs[0][0]
    missing = [attr for attr in args if not hasattr(return_obj, attr)]
    if missing:
        return pytest.ExitCode.TESTS_FAILED, args, missing

    wrong_types = {
        attr: type(getattr(return_obj, attr)) for attr, type_hint in kwargs.items() if not isinstance(getattr(return_obj, attr, None), type_hint)
    }
    if wrong_types:
        return pytest.ExitCode.TESTS_FAILED, kwargs, wrong_types

    return pytest.ExitCode.OK


@_log
def calls(case: TestCase, outputs: tuple, caller: str, **callees: list[tuple[tuple, dict]]) -> _AssertionResult:
    """
    Test if function 'caller' of imported module calls callees in the prescribed manner.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs ``(positional, named, elapsed)`` from student submission.
        The module or class under test is taken from ``outputs[0][0]``.
    caller : str
        Name of the function to call on the object.
    **callees : list of tuple
        Mapping of callee names to lists of ``(args, kwargs)`` expected call tuples.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all calls match, otherwise a failure tuple.
    """
    from contextlib import ExitStack
    from unittest.mock import call, patch

    if not outputs[0]:
        return pytest.ExitCode.TESTS_FAILED, "expected object", "no return object"

    obj = outputs[0][0]
    if not isinstance(obj, (type, types.ModuleType)):
        return pytest.ExitCode.TESTS_FAILED, "type or module", type(obj).__name__

    result = None

    with ExitStack() as stack:
        mocks = {callee: stack.enter_context(patch.object(obj, callee, wraps=getattr(obj, callee))) for callee in callees}
        getattr(obj, caller)()

    for callee, mock in mocks.items():
        expected_calls = [call(*a, **kw) for a, kw in callees.get(callee)]
        if expected_calls != mock.mock_calls:
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected_calls,
                mock.mock_calls,
            )

    return result or pytest.ExitCode.OK


@_log
def equal_contents(case: TestCase, outputs: tuple, *args: str, **kwargs: object) -> _AssertionResult:
    """
    Test if containers have equal contents between actual and expected outputs.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs from student submission.
    *args : str
        Variable names which hold containers to be tested.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all pairs of containers have equal contents,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    # TODO: Collect unequal results in a sensible manner.
    # Upon completion, return (code, expected, actual)

    result = None

    expected_args_types = [type(arg) for arg in case.expected[0]]
    expected_kwargs_types = [type(case.expected[1][key]) for key in args]

    if any(t(outputs[1][key]) != case.expected[1][key] for key, t in zip(args, expected_kwargs_types)):
        wrong_outputs = {x: outputs[1][x] for x in outputs[1] if x in case.expected[1]}
        result = (
            pytest.ExitCode.TESTS_FAILED,
            case.expected[1],
            wrong_outputs,
        )
    if any(t(value) != expected for t, value, expected in zip(expected_args_types, outputs[0], case.expected[0])):
        result = (
            pytest.ExitCode.TESTS_FAILED,
            case.expected[0],
            outputs[0],
        )

    return result or pytest.ExitCode.OK


@_log
def almost_equal(case: TestCase, outputs: tuple, *args: str, atol: float = 1e-7, rtol: float = 1e-7, **kwargs: object) -> _AssertionResult:
    """
    Test for closeness between actual and expected TestCase outputs.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs from student submission.
    *args : str
        Variable names for which near equality is tested.
    atol : float, optional
        Absolute tolerance, by default 1e-7.
    rtol : float, optional
        Relative tolerance, by default 1e-7.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all values are equal up to tolerance,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    import itertools

    result = None

    comparisons = itertools.chain(
        enumerate(itertools.zip_longest(outputs[0], case.expected[0])),
        [(key, (outputs[1][key], case.expected[1][key])) for key in args],
    )

    for index, (output, expect) in comparisons:
        try:
            np.testing.assert_allclose(output, expect, atol=atol, rtol=rtol)

        except TypeError:
            logging.info(
                "Cannot test item %s for near equality.\n output = %s, expect = %s\nTesting for strict equality instead.",
                index,
                output,
                expect,
            )
            if expect != output:
                result = (pytest.ExitCode.TESTS_FAILED, case.expected, outputs)

        except AssertionError:
            result = (pytest.ExitCode.TESTS_FAILED, case.expected, outputs)

    return result or pytest.ExitCode.OK


@_log
def raises(case: TestCase, outputs: tuple | Exception, *args: type[Exception], **kwargs: object) -> _AssertionResult:
    """
    Test if case raised an exception as prescribed.

    Parameters
    ----------
    case : TestCase
        Test case with ``raises`` flag indicating expected exception.
    outputs : tuple or Exception
        Actual outputs or raised exception from student submission.
    *args : type
        Exception types that are expected to be raised.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if the expected exception was raised,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None
    if case.raises:
        logging.debug("Execution is expected to raise %s", args)
        if not any(isinstance(outputs, exception) for exception in args):
            result = (pytest.ExitCode.TESTS_FAILED, args, outputs)
    return result or pytest.ExitCode.OK


@_log
def file_contents(case: TestCase, outputs: tuple, *args: object, **kwargs: object) -> _AssertionResult:
    """
    Test if files in TestCase.expected[1] have the prescribed contents.

    Parameters
    ----------
    case : TestCase
        Test case with ``expected[1]`` mapping filenames to expected contents.
    outputs : tuple
        Actual outputs from student submission (unused by this assertion).
    *args : tuple
        Unused positional arguments.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if contents are bitwise identical,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None

    for filename, contents in case.expected[1].items():
        with pathlib.Path(filename).open("rb") as file:
            actual_contents = file.read()
            if actual_contents != contents:
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    contents,
                    actual_contents,
                )

    return result or pytest.ExitCode.OK


@_log
def equal_value(case: TestCase, outputs: tuple, *args: str, **kwargs: object) -> _AssertionResult:
    """
    Test for exact equality between expected and actual TestCase outputs.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs from student submission.
    *args : str
        Variable names for which exact equality is tested.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all values are exactly equal,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None
    import itertools

    # TODO: Return expected and actual outputs in a sensible manner.
    comparisons = itertools.chain(
        itertools.zip_longest(outputs[0], case.expected[0], fillvalue=None),
        [(outputs[1][key], case.expected[1][key]) for key in args],
    )

    if any(output != expect for output, expect in comparisons):
        result = (pytest.ExitCode.TESTS_FAILED, case.expected, outputs)

    return result or pytest.ExitCode.OK


@_log
def equal_types(case: TestCase, outputs: tuple, *args: str, **kwargs: object) -> _AssertionResult:
    """
    Test for equal types between expected and actual TestCase outputs.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs from student submission.
    *args : str
        Variable names to check.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if all values have equal types,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None

    if not all(isinstance(outputs[1][key], type(case.expected[1][key])) for key in args):
        actual_types = {key: type(outputs[1][key]) for key in args}
        expected_types = {key: type(case.expected[1][key]) for key in args}
        result = (pytest.ExitCode.TESTS_FAILED, expected_types, actual_types)

    return result or pytest.ExitCode.OK


@_log
def equal_scope(case: TestCase, outputs: tuple, *args: object, **kwargs: object) -> _AssertionResult:
    """
    Test for equal scope between expected and actual TestCase outputs.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs from student submission.
    *args : tuple
        Unused positional arguments.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if expected and actual have equal variable names,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None

    output_vars = set(outputs[1].keys())
    expected_vars = set(case.expected[1].keys())
    if output_vars != expected_vars:
        result = (pytest.ExitCode.TESTS_FAILED, expected_vars, output_vars)

    return result or pytest.ExitCode.OK


@_log
def time_bounds(case: TestCase, outputs: tuple, *args: object, **kwargs: object) -> _AssertionResult:
    """
    Test for execution time within bounds, if provided.

    Parameters
    ----------
    case : TestCase
        Test case with ``timing`` tuple of ``(lower, upper)`` bounds.
    outputs : tuple
        Actual outputs; ``outputs[2]`` is the execution time.
    *args : tuple
        Unused positional arguments.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if execution time is within bounds,
        otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    result = None
    execution_time = outputs[2]

    if not (case.timing[0] or 0) < execution_time < (case.timing[1] or 2 * execution_time):
        result = (
            pytest.ExitCode.TESTS_FAILED,
            f"in {case.timing}",
            execution_time,
        )

    return result or pytest.ExitCode.OK
