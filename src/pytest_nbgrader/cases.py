"""
Classes for test cases using code objects or functions.

Export classes for TestCases, listing ``*args`` and ``**kwargs`` for inputs and
(both actual and expected) outputs from a student submission:
- TestCase: Data class for storing inputs and expected outputs of tests.
- Test: Class for executing submissions on TestCases.
"""

from __future__ import annotations


__version__ = "0.3"

__all__ = ["TestCase", "TestSubtask", "Timer", "execute", "format_result", "raised_by_submission", "registered_module"]

import collections.abc
import contextlib
import functools
import importlib.machinery
import importlib.util
import logging
import sys
import types
from copy import deepcopy
from dataclasses import dataclass, field
from time import perf_counter

import numpy as np
import pytest


logger = logging.getLogger(__name__)

_RAISED_BY_SUBMISSION = "_pytest_nbgrader_raised_by_submission"


class _RunningSubmission:
    """Context manager marking exceptions raised inside the block as raised by the student submission."""

    def __enter__(self) -> None:
        """Enter the block running student code."""

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: types.TracebackType | None) -> bool:
        """
        Tag the exception (if any) and let it propagate.

        Parameters
        ----------
        exc_type : type or None
            Exception type, if any.
        exc_value : BaseException or None
            Exception value, if any.
        traceback : types.TracebackType or None
            Traceback, if any.

        Returns
        -------
        bool
            False, so that the exception propagates.
        """
        if isinstance(exc_value, (Exception, SystemExit)):
            # object.__setattr__ also works for exceptions that forbid attribute assignment (e.g. frozen dataclasses)
            with contextlib.suppress(AttributeError, TypeError):
                object.__setattr__(exc_value, _RAISED_BY_SUBMISSION, True)
        return False


def raised_by_submission(exception: BaseException) -> bool:
    """
    Tell whether an exception was raised by student code rather than by the plugin.

    Parameters
    ----------
    exception : BaseException
        Exception raised by :func:`execute`.

    Returns
    -------
    bool
        True if the exception originates from the submission itself.
    """
    return getattr(exception, _RAISED_BY_SUBMISSION, False)


class _RegisteredModule:
    """
    Context manager registering a module in ``sys.modules`` while its code runs.

    Parameters
    ----------
    module : types.ModuleType
        The module about to be executed.
    """

    def __init__(self, module: types.ModuleType) -> None:
        """
        Store the module to register.

        Parameters
        ----------
        module : types.ModuleType
            The module about to be executed.
        """
        self.module = module
        self.previous: types.ModuleType | None = None

    def __enter__(self) -> types.ModuleType:
        """
        Register the module.

        Returns
        -------
        types.ModuleType
            The registered module.
        """
        self.previous = sys.modules.get(self.module.__name__)
        sys.modules[self.module.__name__] = self.module
        return self.module

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: types.TracebackType | None) -> None:
        """
        Restore the previous ``sys.modules`` entry.

        Parameters
        ----------
        exc_type : type or None
            Exception type, if any.
        exc_value : BaseException or None
            Exception value, if any.
        traceback : types.TracebackType or None
            Traceback, if any.
        """
        if self.previous is None:
            sys.modules.pop(self.module.__name__, None)
        else:
            sys.modules[self.module.__name__] = self.previous


def registered_module(module: types.ModuleType) -> _RegisteredModule:
    """
    Register a module in ``sys.modules`` while its code runs, as ``import`` would.

    Parameters
    ----------
    module : types.ModuleType
        The module about to be executed.

    Returns
    -------
    _RegisteredModule
        Context manager that restores the previous ``sys.modules`` entry on exit.
    """
    return _RegisteredModule(module)


class Timer:
    """Context manager for measuring execution time."""

    start: float
    end: float | None

    def __enter__(self) -> Timer:
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

    def __exit__(self, *_exc_args: object) -> None:
        """
        Exit the timer context and record end time.

        Parameters
        ----------
        *_exc_args : object
            Exception info passed by the context manager protocol.
        """
        self.end = perf_counter()

    @property
    def elapsed(self) -> float:
        """
        Elapsed time in seconds.

        Returns
        -------
        float
            Elapsed time since entering the context.
        """
        return (self.end or perf_counter()) - self.start


def _format_call(inputs: tuple[tuple, dict]) -> str:
    """
    Format a single ``(args, kwargs)`` pair as a call signature.

    Parameters
    ----------
    inputs : tuple
        A ``(args, kwargs)`` pair.

    Returns
    -------
    str
        Comma-separated arguments.
    """
    args, kwargs = inputs
    return ", ".join(map(str, (*args, *(f"{k}={v}" for k, v in dict(kwargs).items()))))


def _format_inputs(inputs: tuple[tuple, dict] | list[tuple[tuple, dict]]) -> str:
    """
    Format test case inputs of any supported shape.

    Parameters
    ----------
    inputs : tuple or list
        A single ``(args, kwargs)`` pair, or a list of such pairs (class submissions).

    Returns
    -------
    str
        Human-readable inputs; falls back to ``repr`` for unexpected shapes.
    """
    try:
        if len(inputs) == 2 and isinstance(inputs[1], dict):
            return _format_call(inputs)
        return "; ".join(_format_call(pair) for pair in inputs)
    except Exception:  # noqa: BLE001 - formatting must never hide the actual test result
        return repr(inputs)


def format_result(
    inputs: tuple[tuple, dict] | list[tuple[tuple, dict]],
    result: pytest.ExitCode,
    message: str | None = None,
    exception: str | None = None,
) -> str:
    """
    Format case result for logging nicely.

    Parameters
    ----------
    inputs : tuple or list
        A ``(args, kwargs)`` pair of test case inputs, or a list of such pairs for class submissions.
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
    case = _format_inputs(inputs)

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

    __test__ = False  # not a pytest test class, despite the name

    inputs: tuple[tuple, dict] = field(default_factory=lambda: (tuple(), {}))
    expected: tuple[tuple, dict] = field(default_factory=lambda: (tuple(), {}))
    raises: bool = False
    timing: tuple[float | None, float | None] = (None, None)


@dataclass
class TestSubtask:
    """Test cases, prerequisites, and assertions for a single subtask."""

    __test__ = False  # not a pytest test class, despite the name

    cases: list[TestCase]
    assertions: dict
    prerequisites: dict = field(default_factory=dict)


@functools.singledispatch
def execute(submission: object, case: TestCase) -> tuple[tuple, dict, float]:
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


def _as_outputs(return_value: object, expected_count: int) -> tuple:
    """
    Normalise a function's return value to a tuple of positional outputs.

    With several expected outputs, tuples, lists and arrays hold one output per element;
    any other value (e.g. a string) is a single output.

    Parameters
    ----------
    return_value : object
        Value returned by the submission.
    expected_count : int
        Number of expected positional outputs.

    Returns
    -------
    tuple
        The positional outputs.
    """
    if expected_count == 1:
        return (return_value,)
    if return_value is None:
        return ()
    if isinstance(return_value, (tuple, list)) or (isinstance(return_value, np.ndarray) and return_value.ndim > 0):
        return tuple(return_value)
    return (return_value,)


@execute.register(collections.abc.Callable)
@execute.register(types.FunctionType)
def _execute_function(submission: collections.abc.Callable, case: TestCase) -> tuple[tuple, dict, float]:
    """
    Execute a function (or any other non-class callable) with test case inputs.

    Parameters
    ----------
    submission : callable
        The student function to call.
    case : TestCase
        Test case providing inputs and expected output count.

    Returns
    -------
    tuple[tuple, dict, float]
        A ``(positional_outputs, named_outputs, elapsed_time)`` triple.
    """
    input_args, input_kwargs = deepcopy(case.inputs)
    input_args, input_kwargs = tuple(input_args), dict(input_kwargs)
    with Timer() as t, _RunningSubmission():
        return_value = submission(*input_args, **input_kwargs)

    number_of_expected_args = len(case.expected[0])
    output_args = _as_outputs(return_value, number_of_expected_args)

    if number_of_expected_args != len(output_args) and not case.raises:
        logger.warning("Number of expected outputs (%s) does not match number of actual outputs (%s)!", number_of_expected_args, len(output_args))

    return output_args, {}, t.elapsed


@execute.register
def _(submission: types.CodeType, case: TestCase) -> tuple[tuple, dict, float]:
    """
    Execute bytecode submission with given input scope.

    The code runs with ``__name__ == "__main__"``, as in a notebook cell. Dunder names
    (``__builtins__``, ``__annotations__``, ...) are not part of the returned scope.

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
    positional, scope = deepcopy(case.inputs)
    scope = {"__name__": "__main__", **scope}
    with Timer() as t, _RunningSubmission():
        exec(submission, scope)

    named = {key: value for key, value in scope.items() if not (key.startswith("__") and key.endswith("__"))}
    return positional, named, t.elapsed


@execute.register
def _(submission: importlib.machinery.ModuleSpec, case: TestCase) -> tuple[tuple, dict, float]:
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
        with registered_module(return_object), _RunningSubmission():
            submission.loader.exec_module(return_object)
    return (return_object,), {}, t.elapsed


@execute.register
def _(submission: type, case: TestCase) -> tuple[tuple, dict, float]:
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
    instantiations = [(tuple(args), dict(kwargs)) for args, kwargs in deepcopy(case.inputs)]
    return_objects = []
    with Timer() as t:
        for args, kwargs in instantiations:
            with _RunningSubmission():
                return_objects.append(submission(*args, **kwargs))
    return tuple(return_objects), {}, t.elapsed
