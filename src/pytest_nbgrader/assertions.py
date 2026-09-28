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

import contextlib
import functools
import inspect
import itertools
import logging
import pathlib
import types
import warnings
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pytest

from pytest_nbgrader.cases import TestCase


_AssertionResult = pytest.ExitCode | tuple[pytest.ExitCode, Any, Any]

_SENTINEL = object()

_VisibleDeprecationWarning = getattr(np, "exceptions", np).VisibleDeprecationWarning


def _equal(actual: object, expected: object) -> bool:
    """
    Compare two values for exact equality, including numpy arrays.

    Parameters
    ----------
    actual : object
        Value produced by the submission.
    expected : object
        Expected value.

    Returns
    -------
    bool
        True if the values are equal.
    """
    if isinstance(actual, np.ndarray) or isinstance(expected, np.ndarray):
        try:
            return bool(np.array_equal(actual, expected))
        except (TypeError, ValueError):
            return False
    with contextlib.suppress(TypeError, ValueError):
        return bool(actual == expected)
    # e.g. containers holding numpy arrays, whose == is element-wise: compare item by item
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_equal(actual[key], expected[key]) for key in expected)
    if (isinstance(actual, list) and isinstance(expected, list)) or (isinstance(actual, tuple) and isinstance(expected, tuple)):
        return len(actual) == len(expected) and all(_equal(a, e) for a, e in zip(actual, expected, strict=True))
    return False


def _close(actual: object, expected: object, **tolerances: float) -> bool:
    """
    Compare two values for closeness, falling back to exact equality for non-numeric values.

    Parameters
    ----------
    actual : object
        Value produced by the submission.
    expected : object
        Expected value.
    **tolerances : float
        Tolerances forwarded to ``np.testing.assert_allclose``.

    Returns
    -------
    bool
        True if the values have the same shape and are equal up to tolerance.
    """
    try:
        with warnings.catch_warnings():
            # numpy < 1.24 warns about ragged sequences instead of raising ValueError
            warnings.simplefilter("ignore", _VisibleDeprecationWarning)
            # assert_allclose broadcasts, so e.g. a scalar would match any array of that value
            if np.shape(actual) != np.shape(expected):
                return False
            np.testing.assert_allclose(actual, expected, **tolerances)
    except AssertionError:
        return False
    except (TypeError, ValueError):
        logging.info("Cannot test %r and %r for near equality, testing for exact equality instead.", actual, expected)
        return _equal(actual, expected)
    return True


def _is_harness_output(outputs: object) -> bool:
    """
    Tell whether outputs have the ``(positional, named, elapsed)`` shape produced by ``execute``.

    Parameters
    ----------
    outputs : object
        Outputs passed to an assertion.

    Returns
    -------
    bool
        True for harness-shaped outputs.
    """
    return isinstance(outputs, tuple) and len(outputs) == 3 and isinstance(outputs[0], tuple) and isinstance(outputs[1], dict)


def _objects(case: TestCase, outputs: object) -> tuple[Sequence, Sequence]:
    """
    Return the actual and expected objects to compare attribute by attribute.

    Harness-shaped outputs and ``(args, kwargs)``-shaped expectations are unpacked; bare objects
    (as passed by custom harnesses) are used as they are.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : object
        Actual outputs, or a bare actual object.

    Returns
    -------
    tuple
        ``(actual_objects, expected_objects)``.
    """
    expected = case.expected
    if isinstance(expected, (tuple, list)) and len(expected) == 2 and isinstance(expected[0], (tuple, list)) and isinstance(expected[1], dict):
        expected_objects = expected[0]
    else:
        expected_objects = (expected,)
    actual_objects = outputs[0] if _is_harness_output(outputs) else (outputs,)
    return actual_objects, expected_objects


def _undefined(outputs: tuple, names: tuple[str, ...]) -> list[str]:
    """
    List the named outputs that the submission did not define.

    Parameters
    ----------
    outputs : tuple
        Actual outputs ``(positional, named, elapsed)``.
    names : tuple of str
        Names that are compared.

    Returns
    -------
    list of str
        Names missing from ``outputs[1]``.
    """
    return [name for name in names if name not in outputs[1]]


_CONTAINER_TYPES = (dict, frozenset, set, list, tuple)


def _contents_equal(actual: object, expected: object) -> bool:
    """
    Compare container contents, casting the actual container to the expected container type.

    Parameters
    ----------
    actual : object
        Value produced by the submission.
    expected : object
        Expected value.

    Returns
    -------
    bool
        True if the contents are equal. Scalars are compared without any cast.
    """
    if isinstance(expected, np.ndarray):
        try:
            return bool(np.array_equal(np.asarray(actual), expected))
        except (TypeError, ValueError):
            return False
    container_type = next((t for t in _CONTAINER_TYPES if isinstance(expected, t)), None)
    if container_type is not None and not isinstance(actual, (str, bytes)):
        try:
            actual, expected = container_type(actual), container_type(expected)
        except (TypeError, ValueError):
            return False
    return _equal(actual, expected)


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
            if isinstance(result, pytest.ExitCode):
                result, expect, actual = result, case.expected, outputs
            else:
                result, expect, actual = result
            message = f"{name} failed with result {getattr(result, 'name', result)}.\nExpected: {expect},\nActual: {actual}.\n"

        return result, message

    return wrapper


@_log
def close_attributes(case: TestCase, outputs: object, *args: str, **kwargs: float) -> _AssertionResult:
    """
    Assert close values for given attributes between expected and outputs.

    Like ``equal_attributes``, every object in ``outputs[0]`` is compared with the
    corresponding object in ``case.expected[0]``. Bare objects (as passed by custom
    harnesses) are accepted as well.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : object
        Actual outputs ``(positional, named, elapsed)``, or a bare object whose attributes are compared.
    *args : str
        Attribute names to compare.
    **kwargs : dict
        Tolerances forwarded to ``np.testing.assert_allclose``.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` on success, or a failure tuple.
    """
    actual_objects, expected_objects = _objects(case, outputs)
    if not actual_objects or len(actual_objects) != len(expected_objects):
        return pytest.ExitCode.TESTS_FAILED, f"{len(expected_objects)} object(s)", f"{len(actual_objects)} object(s)"

    for actual, expected in zip(actual_objects, expected_objects, strict=True):
        for attribute in args:
            try:
                if not _close(getattr(actual, attribute), getattr(expected, attribute), **kwargs):
                    return pytest.ExitCode.TESTS_FAILED, case.expected, outputs
            except AttributeError:
                return pytest.ExitCode.TESTS_FAILED, case.expected, outputs
    return pytest.ExitCode.OK


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
        Paths of modules that must be imported (``import <stem>``) from exactly that location.
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

    for expected in map(pathlib.Path, args):
        imported = getattr(return_obj, expected.stem, None)
        actual = inspect.getmodule(imported) if imported is not None else None
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
        value = getattr(return_obj, obj, _SENTINEL)
        if value is _SENTINEL:
            logging.warning("%s is not defined.", obj)
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected or "locally defined",
                "not defined",
            )
            continue
        actual = inspect.getmodule(value)
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
    Test if all attributes of expected and actual return objects are equal.

    Parameters
    ----------
    case : TestCase
        Test case with expected outputs.
    outputs : tuple
        Actual outputs ``(positional, named, elapsed)`` from student submission.
        Every object in ``outputs[0]`` (e.g. one per instantiation of a class) is
        compared with the corresponding object in ``case.expected[0]``.
    *args : str
        Attribute names to compare.
    **kwargs : dict
        Unused keyword arguments.

    Returns
    -------
    Enum
        ``pytest.ExitCode.OK`` if equal, otherwise ``pytest.ExitCode.TESTS_FAILED``.
    """
    actual_objects, expected_objects = _objects(case, outputs)
    if not actual_objects or len(actual_objects) != len(expected_objects):
        return pytest.ExitCode.TESTS_FAILED, f"{len(expected_objects)} object(s)", f"{len(actual_objects)} object(s)"

    for actual, expected in zip(actual_objects, expected_objects, strict=True):
        for attr in args:
            if not hasattr(actual, attr) or not _equal(getattr(actual, attr), getattr(expected, attr, _SENTINEL)):
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
        attr: type(getattr(return_obj, attr, None))
        for attr, type_hint in kwargs.items()
        if not isinstance(getattr(return_obj, attr, None), type_hint)
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

    missing = [name for name in (caller, *callees) if not hasattr(obj, name)]
    if missing:
        return pytest.ExitCode.TESTS_FAILED, [caller, *callees], f"missing: {missing}"

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

    Actual containers are cast to the expected container type (e.g. a list where a tuple
    was expected) before comparing. Missing or extra outputs fail.

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
    missing = _undefined(outputs, args)
    if missing:
        return pytest.ExitCode.TESTS_FAILED, f"variables {list(args)} to be defined", f"undefined: {missing}"

    if any(not _contents_equal(outputs[1][key], case.expected[1][key]) for key in args):
        wrong_outputs = {x: outputs[1][x] for x in outputs[1] if x in case.expected[1]}
        return pytest.ExitCode.TESTS_FAILED, case.expected[1], wrong_outputs

    if len(outputs[0]) != len(case.expected[0]) or any(
        not _contents_equal(value, expected) for value, expected in zip(outputs[0], case.expected[0], strict=True)
    ):
        return pytest.ExitCode.TESTS_FAILED, case.expected[0], outputs[0]

    return pytest.ExitCode.OK


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
    missing = _undefined(outputs, args)
    if missing:
        return pytest.ExitCode.TESTS_FAILED, f"variables {list(args)} to be defined", f"undefined: {missing}"

    if len(outputs[0]) != len(case.expected[0]):
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs

    comparisons = itertools.chain(
        zip(outputs[0], case.expected[0], strict=True),
        [(outputs[1][key], case.expected[1][key]) for key in args],
    )

    if not all(_close(output, expect, atol=atol, rtol=rtol) for output, expect in comparisons):
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs

    return pytest.ExitCode.OK


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
        try:
            actual_contents = pathlib.Path(filename).read_bytes()
        except FileNotFoundError:
            result = (pytest.ExitCode.TESTS_FAILED, contents, f"{filename} not found")
            continue
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
    missing = _undefined(outputs, args)
    if missing:
        return pytest.ExitCode.TESTS_FAILED, f"variables {list(args)} to be defined", f"undefined: {missing}"

    if len(outputs[0]) != len(case.expected[0]):
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs

    comparisons = itertools.chain(
        zip(outputs[0], case.expected[0], strict=True),
        [(outputs[1][key], case.expected[1][key]) for key in args],
    )

    if not all(_equal(output, expect) for output, expect in comparisons):
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs

    return pytest.ExitCode.OK


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

    missing = _undefined(outputs, args)
    if missing:
        return pytest.ExitCode.TESTS_FAILED, f"variables {list(args)} to be defined", f"undefined: {missing}"

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
    lower, upper = case.timing

    if not ((lower is None or execution_time >= lower) and (upper is None or execution_time <= upper)):
        result = (
            pytest.ExitCode.TESTS_FAILED,
            f"in {case.timing}",
            execution_time,
        )

    return result or pytest.ExitCode.OK


# In ``raises=True`` cases the harness passes the raised exception as ``outputs``. These assertions
# compare outputs and do not apply to exceptions, so the harness does not call them in that case.
# Custom assertions without this attribute (and file_contents, which ignores outputs) are called.
for _assertion in (
    almost_equal,
    calls,
    close_attributes,
    equal_attributes,
    equal_contents,
    equal_scope,
    equal_types,
    equal_value,
    has_import,
    has_method,
    time_bounds,
):
    _assertion.accepts_exceptions = False  # type: ignore[attr-defined]
