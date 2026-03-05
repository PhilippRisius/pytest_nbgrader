"""
Classes for test cases using code objects or functions.

Export classes for TestCases, listing *args and **kwargs for inputs and
(both actual and expected) outputs from a student submission:
- TestCase: Data class for storing inputs and expected outputs of tests.
- Test: Class for executing submissions on TestCases.
"""

__version__ = "0.3"

import functools
import importlib.machinery
import importlib.util
import logging
import types
from copy import deepcopy
from dataclasses import dataclass, field
from time import perf_counter

import pytest


logger = logging.getLogger(__name__)


class Timer:
    """Context manager for measuring execution time."""

    def __enter__(self):
        """
        Enter the timer context and record start time.

        Returns
        -------
        Timer
            The timer instance.
        """
        self.start = perf_counter()
        self.end = None
        return self

    def __exit__(self, *exc_args):
        """
        Exit the timer context and record end time.

        Parameters
        ----------
        *exc_args : tuple
            Exception info passed by the context manager protocol.
        """
        self.end = perf_counter()

    @property
    def elapsed(self):
        """
        Return elapsed time in seconds.

        Returns
        -------
        float
            Elapsed time since entering the context.
        """
        return (self.end or perf_counter()) - self.start


def format_result(inputs, result, message=None, exception=None):
    """
    Format case result for logging nicely.

    Parameters
    ----------
    inputs : tuple
        A ``(args, kwargs)`` pair of test case inputs.
    result : Enum
        The pytest exit code for this case.
    message : str or None, optional
        Failure message, by default None.
    exception : str or None, optional
        Formatted traceback, by default None.

    Returns
    -------
    str
        Formatted result string.
    """
    case = ", ".join(
        map(
            str,
            inputs[0] + tuple(f"{k}={v}" for k, v in inputs[1].items()),
        )
    )

    if result is pytest.ExitCode.INTERNAL_ERROR:
        formatted_result = f"Test case could not be tested:\n{case}\nThe following exception was raised:\n{exception}\n-----------------\n\n"
    elif result is pytest.ExitCode.TESTS_FAILED:
        formatted_result = f"Test case failed:\n{case}\nThe following message was passed:\n{message}\n-----------------\n\n"
    elif result is pytest.ExitCode.OK:
        formatted_result = f"Test case passed:\n{case}\n-----------------\n\n"
    else:
        formatted_result = f"Unexpected result: {result}\n{case}\n------------------\n\n"

    return formatted_result


@dataclass
class TestCase:
    """Inputs and expected outputs of a single test case."""

    inputs: tuple[tuple, dict] = field(default_factory=lambda: (tuple(), {}))
    expected: tuple[tuple, dict] = field(default_factory=lambda: (tuple(), {}))
    raises: bool = False
    timing: tuple = (None, None)


@dataclass
class TestSubtask:
    """Test cases, prerequisites, and assertions for a single subtask."""

    cases: list[TestCase]
    assertions: dict
    prerequisites: dict = field(default_factory=dict)


@functools.singledispatch
def execute(submission, case) -> tuple[tuple, dict, float]:
    """
    Execute a submission on a test case.

    Parameters
    ----------
    submission : object
        The student submission to execute.
    case : TestCase
        Test case with inputs and expected outputs.

    Returns
    -------
    tuple[tuple, dict, float]
        A ``(positional_outputs, named_outputs, elapsed_time)`` triple.
    """
    raise NotImplementedError(f"Cannot run {type(submission) = }.")


@execute.register
def _(submission: types.FunctionType, case) -> tuple[tuple, dict, float]:
    """
    Execute a function submission with test case inputs.

    Parameters
    ----------
    submission : types.FunctionType
        The student function to call.
    case : TestCase
        Test case providing inputs and expected output count.

    Returns
    -------
    tuple[tuple, dict, float]
        A ``(positional_outputs, named_outputs, elapsed_time)`` triple.
    """
    input_args, input_kwargs = deepcopy(case.inputs)
    with Timer() as t:
        return_value = submission(*input_args, **input_kwargs)

    number_of_expected_args = len(case.expected[0])

    if return_value is None:
        output_args = tuple()
    elif number_of_expected_args == 1:
        output_args = (return_value,)
    else:
        output_args = return_value

    if number_of_expected_args != len(output_args) and not case.raises:
        logger.warning(f"Number of expected outputs ({number_of_expected_args}) does not match number of actual outputs ({len(output_args)})!")

    return output_args, {}, t.elapsed


@execute.register
def _(submission: types.CodeType, case) -> tuple[tuple, dict, float]:
    """
    Execute bytecode submission with given input scope.

    Parameters
    ----------
    submission : types.CodeType
        Compiled bytecode from student solution.
    case : TestCase
        Test case providing input scope as ``inputs[1]``.

    Returns
    -------
    tuple[tuple, dict, float]
        A ``(positional_outputs, named_outputs, elapsed_time)`` triple.
    """
    outputs = deepcopy(case.inputs)
    with Timer() as t:
        exec(submission, outputs[1])

    # subtract scope from empty code
    pytest_scope = {}
    exec(compile("", "", "exec"), pytest_scope)

    outputs = (
        outputs[0],
        {key: value for key, value in outputs[1].items() if key not in pytest_scope},
        t.elapsed,
    )

    return outputs


@execute.register
def _(submission: importlib.machinery.ModuleSpec, case) -> tuple[tuple, dict, float]:
    """
    Import a module from spec and store the return object.

    Parameters
    ----------
    submission : importlib.machinery.ModuleSpec
        Module specification to import.
    case : TestCase
        Unused test case (module import ignores inputs).

    Returns
    -------
    tuple[tuple, dict, float]
        A ``(positional_outputs, named_outputs, elapsed_time)`` triple.
    """
    with Timer() as t:
        return_object = importlib.util.module_from_spec(submission)
        submission.loader.exec_module(return_object)
    return (return_object,), {}, t.elapsed


@execute.register
def _(submission: type, case) -> tuple[tuple, dict, float]:
    """
    Instantiate a class submission with test case inputs.

    Parameters
    ----------
    submission : type
        The class to instantiate.
    case : TestCase
        Test case providing ``inputs`` as list of ``(args, kwargs)`` pairs.

    Returns
    -------
    tuple[tuple, dict, float]
        A ``(positional_outputs, named_outputs, elapsed_time)`` triple.
    """
    with Timer() as t:
        return_objects = tuple(submission(*args, **kwargs) for args, kwargs in case.inputs)
    return return_objects, {}, t.elapsed
