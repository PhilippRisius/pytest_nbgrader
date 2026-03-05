"""Check submissions with pytest and fixtures."""

import traceback

import pytest

from pytest_nbgrader.cases import execute, format_result


class TestClass:
    """Generic pytest class."""

    @pytest.mark.tryfirst
    def test_prerequisites(cls, submission, prerequisites) -> None:
        """Run prerequisites tests against student submission."""
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
    def test_execution(cls, submission, cases, verbosity) -> tuple:
        """Run student submission on test cases."""
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

    def test_assertion(cls, test_execution, assertions, verbosity) -> None:
        """Run assertions against results of test execution (pytest fixture)."""
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
