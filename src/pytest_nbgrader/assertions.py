"""Module for testing actual and expected outputs of a TestCase.

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

__version__ = "0.3"

import functools
import inspect
import logging
import types
from enum import Enum

import numpy as np
import pytest
from pytest_nbgrader.cases import TestCase


def _log(
    assertion,
    name: str = "",
):
    """Log failures and successes of running assertions."""
    name = f'Assertion "{name or assertion.__name__}"'

    @functools.wraps(assertion)
    def wrapper(case, outputs, *args, **kwargs):
        """Append a message to the test result."""
        result = assertion(case, outputs, *args, **kwargs)
        if result is pytest.ExitCode.OK:
            logging.debug(f"{name} succeeded:\nExpected: {case.expected}\nActual: {outputs}\n")
            message = ""
        else:
            result, expect, actual = result
            message = f"{name} failed with result {result}.\nExpected: {expect},\nActual: {actual}.\n"

        return result, message

    return wrapper


@_log
def close_attributes(case: TestCase, outputs, *args, **kwargs):
    """assert close values for given attributes between expected and outputs."""

    try:
        expected_attrs, output_attrs = ([getattr(instance, attribute) for attribute in args] for instance in (case.expected, outputs))
        np.testing.assert_allclose(expected_attrs, output_attrs, **kwargs)
        return pytest.ExitCode.OK
    except AssertionError:
        return pytest.ExitCode.TESTS_FAILED, case.expected, outputs


@_log
def has_import(case: TestCase, *args, **kwargs) -> Enum:
    """Test if an object has a module-level import."""
    # TODO: collect results and yield a suitable return message
    #       with all discrepancies.

    import pathlib

    def invalid_import(name, expected=None, actual=None):
        """format message for warning about invalid imports"""
        message = f"{name} was not imported"
        if expected or actual:
            expected = expected or "locally defined"
            actual = actual or "locally defined"
            message += f" from expected location.\n expected: {expected}, actual: {actual}"
        return message + "."

    result = None
    cwd = pathlib.Path.cwd()

    for expected in args:
        actual = inspect.getmodule(getattr(case.return_object, expected))
        if actual is None:
            logging.warning(invalid_import(expected.stem, expected, "not imported"))
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected.stem,
                "not imported",
            )
        else:
            actual_name = actual.__spec__.name
            actual_origin = pathlib.Path(actual.__spec__.origin).relative_to(cwd)
            if (expected.stem, expected) != (actual_name, actual_origin):
                logging.warning(invalid_import(expected.stem, expected, actual_origin))
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    expected.stem,
                    actual_name,
                )

    for obj, expected in kwargs.items():
        actual = inspect.getmodule(getattr(case.return_object, obj))
        if actual is not None:
            actual_name = actual.__spec__.name
            actual_origin = pathlib.Path(actual.__spec__.origin).relative_to(cwd)
            if expected is None:
                logging.warning(invalid_import(obj, None, actual_origin))
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    "locally defined",
                    actual_origin,
                )
            elif (expected.stem, expected) != (actual_name, actual_origin):
                logging.warning(invalid_import(obj, expected, actual_origin))
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    expected or "locally defined",
                )
            else:
                logging.debug(f'Test "{obj} imported from {expected.stem}" succeeded.')
        elif expected is not None:
            logging.warning(invalid_import(obj, expected, None))
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected,
                actual or "locally defined",
            )
        else:
            logging.debug(f'Test "{obj} was locally defined" succeeded.')

    return result or pytest.ExitCode.OK


def equal_attributes(case: TestCase, *args, **kwargs) -> Enum:
    """Test if all attributes of expected and actual return object are equal."""

    result = None

    if all(getattr(case.return_object, attr) == getattr(case.expected_object, attr) for attr in args):
        result = pytest.ExitCode.TESTS_FAILED

    return result or pytest.ExitCode.OK


def has_method(case: TestCase, *args, **kwargs) -> Enum:
    """Test if return object of TestCase has a given method"""

    result = None

    if all(hasattr(case.return_object, attribute) for attribute in args):
        if not all(
            hasattr(case.return_object, attribute) and isinstance(getattr(case.return_object, attribute), type_hint)
            for attribute, type_hint in kwargs.items()
        ):
            result = pytest.ExitCode.TESTS_FAILED
    else:
        result = pytest.ExitCode.TESTS_FAILED

    return result or pytest.ExitCode.OK


def calls(case: TestCase, caller, **callees):
    """Test if function 'caller' of imported module calls callees in the prescribed manner."""

    from contextlib import ExitStack
    from unittest.mock import call, patch

    result = None

    obj = case.outputs[0][0]
    assert isinstance(obj, type) or isinstance(obj, types.ModuleType)

    with ExitStack() as stack:
        calls = {callee: stack.enter_context(patch.object(obj, callee, wraps=getattr(obj, callee))) for callee in callees}
        getattr(obj, caller)()

    for callee, mock in calls.items():
        expected_calls = [call(*args, **kwargs) for args, kwargs in callees.get(callee)]
        if expected_calls != mock.mock_calls:
            result = (
                pytest.ExitCode.TESTS_FAILED,
                expected_calls,
                mock.mock_calls,
            )

    return result or pytest.ExitCode.OK


@_log
def equal_contents(case, outputs, *args, **kwargs) -> Enum:
    """Test if containers have the same elements, piecewise between actual and expected TestCase outputs.

    case -- TestCase with expected outputs.
    outputs -- actual outputs from a student submission.
    args -- list of variable names which hold containers to be tested.

    Return pytest.ExitCode.OK if all pairs of containers have equal contents, else pytest.ExitCode.TESTS_FAILED.
    Containers may have different types, but the contents must be same.
    Order must be respected iff expected output is an ordered type.
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
def almost_equal(case, outputs, *args, atol: float = 1e-7, rtol: float = 1e-7, **kwargs) -> Enum:
    """Test for closeness, up to tolerance epsilon, between actual and expected TestCase outputs.

    epsilon -- relative tolerance for equality testing.
    case -- TestCase with expected outputs.
    outputs -- actual outputs from a student submission.
    args -- list of variable names for which near equality is tested.

    Return pytest.ExitCode.OK if all values of the case are equal up to epsilon, else pytest.ExitCode.TESTS_FAILED.
    Fall back to strict equality testing for non-numeric types.
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
            logging.info(f"Cannot test item {index} for near equality.\n {output = }, {expect = }\nTesting for strict equality instead.")
            if expect != output:
                result = (pytest.ExitCode.TESTS_FAILED, case.expected, outputs)

        except AssertionError:
            result = (pytest.ExitCode.TESTS_FAILED, case.expected, outputs)

    return result or pytest.ExitCode.OK


@_log
def raises(case, outputs, *args, **kwargs) -> Enum:
    """Test if case raised an exception as prescribed."""
    result = None
    if case.raises:
        logging.debug(f"Execution is expected to raise {args}")
        if not any(isinstance(outputs, exception) for exception in args):
            result = (pytest.ExitCode.TESTS_FAILED, args, outputs)
    return result or pytest.ExitCode.OK


@_log
def file_contents(case: TestCase, *args, **kwargs) -> Enum:
    """Test if files in Testcase.expected[1] have the prescribed contents.

    Parameters:
      case -- TestCaseFunction with filenames: expected contents

    Return pytest.ExitCode.OK if contents of files are bitwise identical, else pytest.ExitCode.TESTS_FAILED.
    """
    result = None

    for filename, contents in case.expected[1].items():
        with open(filename, "rb") as file:
            actual_contents = file.read()
            if actual_contents != contents:
                result = (
                    pytest.ExitCode.TESTS_FAILED,
                    contents,
                    actual_contents,
                )

    return result or pytest.ExitCode.OK


@_log
def equal_value(case, outputs, *args, **kwargs) -> Enum:
    """Test for exact equality between variables *args of expected outputs of a TestCase and actual outputs.

    case -- TestCase with expected outputs.
    outputs -- actual outputs from a student submission
    args -- list of variables for which exact equality is tested.

    Return pytest.ExitCode.OK if all values stored under variable names from args are exactly equal.
    Else, return pytest.ExitCode.TESTS_FAILED.
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
def equal_types(case, outputs, *args, **kwargs) -> Enum:
    """Test for equal types between variables *args of expected outputs of a TestCase and actual outputs.

    case -- TestCase with expected outputs.
    outputs -- actual outputs from a student submission.
    args -- list of variables to check.

    Return pytest.ExitCode.OK if all values stored under variable names from args have equal types.
    Else, return pytest.ExitCode.TESTS_FAILED.
    """
    result = None

    if not all(isinstance(outputs[1][key], type(case.expected[1][key])) for key in args):
        actual_types = {key: type(outputs[1][key]) for key in args}
        expected_types = {key: type(case.expected[1][key]) for key in args}
        result = (pytest.ExitCode.TESTS_FAILED, expected_types, actual_types)

    return result or pytest.ExitCode.OK


@_log
def equal_scope(case, outputs, *args, **kwargs) -> Enum:
    """Test for equal scope expected outputs of a TestCase and actual outputs.

    case -- TestCase with expected outputs.
    outputs -- actual outputs from a student submission.

    Return pytest.ExitCode.OK if case.expected and outputs have equal variables.
    Else, return pytest.ExitCode.TESTS_FAILED.
    """
    result = None

    output_vars = set(outputs[1].keys())
    expected_vars = set(case.expected[1].keys())
    if output_vars != expected_vars:
        result = (pytest.ExitCode.TESTS_FAILED, expected_vars, output_vars)

    return result or pytest.ExitCode.OK


@_log
def time_bounds(case, outputs, *args, **kwargs) -> Enum:
    """Test for execution time within bounds, if provided"""

    result = None
    execution_time = outputs[2]

    if not (case.timing[0] or 0) < execution_time < (case.timing[1] or 2 * execution_time):
        result = (
            pytest.ExitCode.TESTS_FAILED,
            f"in {case.timing}",
            execution_time,
        )

    return result or pytest.ExitCode.OK
