"""Check submissions with pytest and fixtures."""

from __future__ import annotations


__all__ = ["TestClass"]

import traceback

import pytest

from pytest_nbgrader.cases import TestCase, execute, format_result


class TestClass:
    """Generic pytest class."""

    @pytest.mark.tryfirst
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
        function, (args, kwargs) = prerequisites
        if function(submission, *args, **kwargs) is not pytest.ExitCode.OK:
            pytest.fail(
                """
                Student submission does not fulfill prerequisites.\n
                Test cases will be run anyways, but might fail...
                """,
                pytrace=False,
            )

    @pytest.fixture
    def test_execution(self, submission: object, cases: TestCase, verbosity: int) -> tuple[TestCase, tuple[tuple, dict, float] | Exception]:
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
            A ``(case, result)`` pair.
        """
        try:
            result = execute(submission, cases)
        except Exception as e:
            if cases.raises:
                # forward the (expected) exception to be checked
                result = e
            else:
                result = pytest.ExitCode.INTERNAL_ERROR
                limit = (verbosity > 0) - 1
                exception = traceback.format_exc(limit=limit)
                pytest.fail(
                    format_result(cases.inputs, result, exception=exception),
                    pytrace=False,
                )
        return cases, result

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
        function, (args, kwargs) = assertions
        try:
            result, message = function(case, outputs, *args, **kwargs)
            exception = None

        except Exception:
            limit = (verbosity > 0) - 1
            result = pytest.ExitCode.INTERNAL_ERROR
            message = None
            exception = traceback.format_exc(limit=limit)

        if result is not pytest.ExitCode.OK:
            pytest.fail(
                format_result(case.inputs, result, message, exception),
                pytrace=False,
            )
