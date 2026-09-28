"""Check submissions with pytest and fixtures."""

from __future__ import annotations


__all__ = ["TestClass"]

import traceback
from collections.abc import Callable

import pytest

from pytest_nbgrader.cases import TestCase, execute, format_result, raised_by_submission


def _unpack(parameter: tuple) -> tuple[Callable, tuple, dict]:
    """
    Unpack a parametrized prerequisite or assertion.

    Parameters
    ----------
    parameter : tuple
        An item of the prerequisites or assertions dict: either ``(function, (args, kwargs))``
        or ``(label, (function, (args, kwargs)))``.

    Returns
    -------
    tuple
        A ``(function, args, kwargs)`` triple.
    """
    head, spec = parameter
    function, (args, kwargs) = (head, spec) if callable(head) else spec
    return function, args, kwargs


def _traceback_limit(verbosity: int) -> int | None:
    """
    Choose how many traceback frames to report.

    Parameters
    ----------
    verbosity : int
        Verbosity level for output formatting.

    Returns
    -------
    int or None
        ``None`` (full traceback) when verbose, otherwise ``-1`` (innermost frame only).
    """
    return None if verbosity > 0 else -1


class TestClass:
    """Generic pytest class."""

    def test_prerequisites(self, submission: object, prerequisites: tuple) -> None:
        """
        Run prerequisites tests against student submission.

        Parameters
        ----------
        submission : object
            The student submission under test.
        prerequisites : tuple
            A ``(function, (args, kwargs))`` pair for the prerequisite check.
        """
        function, args, kwargs = _unpack(prerequisites)
        if function(submission, *args, **kwargs) is not pytest.ExitCode.OK:
            pytest.fail(
                """
                Student submission does not fulfill prerequisites.\n
                Test cases will be run anyways, but might fail...
                """,
                pytrace=False,
            )

    @pytest.fixture
    def test_execution(self, submission: object, cases: TestCase, verbosity: int) -> tuple[TestCase, tuple[tuple, dict, float] | BaseException]:
        """
        Run student submission on test cases.

        Parameters
        ----------
        submission : object
            The student submission to execute.
        cases : TestCase
            Test case with inputs and expected outputs.
        verbosity : int
            Verbosity level for output formatting.

        Returns
        -------
        tuple
            A ``(case, result)`` pair. For ``raises=True`` cases, ``result`` is the exception
            raised by the submission.
        """
        try:
            return cases, execute(submission, cases)
        except (Exception, SystemExit) as e:
            if cases.raises and raised_by_submission(e):
                # forward the (expected) exception to be checked
                return cases, e
            exception = traceback.format_exc(limit=_traceback_limit(verbosity))
        pytest.fail(
            format_result(cases.inputs, pytest.ExitCode.INTERNAL_ERROR, exception=exception),
            pytrace=False,
        )

    def test_assertion(self, test_execution: tuple, assertions: tuple, verbosity: int) -> None:
        """
        Run assertions against results of test execution.

        Parameters
        ----------
        test_execution : tuple
            A ``(case, outputs)`` pair from the ``test_execution`` fixture.
        assertions : tuple
            A ``(function, (args, kwargs))`` pair for the assertion check.
        verbosity : int
            Verbosity level for output formatting.
        """
        case, outputs = test_execution
        function, args, kwargs = _unpack(assertions)
        if isinstance(outputs, BaseException) and not getattr(function, "accepts_exceptions", False):
            # the expected exception was raised; only exception assertions (``raises``) apply
            return

        try:
            result, message = function(case, outputs, *args, **kwargs)
            exception = None

        except Exception:
            result = pytest.ExitCode.INTERNAL_ERROR
            message = None
            exception = traceback.format_exc(limit=_traceback_limit(verbosity))

        if result is not pytest.ExitCode.OK:
            pytest.fail(
                format_result(case.inputs, result, message, exception),
                pytrace=False,
            )
