"""Tests for harness.py — TestClass test methods."""

from unittest.mock import MagicMock

import pytest

from pytest_nbgrader.cases import TestCase
from pytest_nbgrader.harness import TestClass as HarnessClass


# ---------------------------------------------------------------------------
# test_prerequisites
# ---------------------------------------------------------------------------


class TestPrerequisites:
    """Tests for TestClass.test_prerequisites."""

    def test_ok_passes(self):
        """Prerequisite returning OK does not raise."""

        def fn(sub, *a, **kw):
            return sub and pytest.ExitCode.OK

        prereqs = (fn, ((), {}))
        HarnessClass().test_prerequisites("submission", prereqs)

    def test_failure_calls_pytest_fail(self):
        """Non-OK result triggers pytest.fail with prerequisites message."""

        def fn(sub, *a, **kw):
            return sub and pytest.ExitCode.TESTS_FAILED

        prereqs = (fn, ((), {}))
        with pytest.raises(pytest.fail.Exception, match="prerequisites"):
            HarnessClass().test_prerequisites("submission", prereqs)

    def test_unpacks_args_kwargs(self):
        """Args and kwargs are unpacked and forwarded to the function."""
        mock_fn = MagicMock(return_value=pytest.ExitCode.OK)
        prereqs = (mock_fn, (("pos_arg",), {"key": "val"}))
        HarnessClass().test_prerequisites("sub", prereqs)
        mock_fn.assert_called_once_with("sub", "pos_arg", key="val")


# ---------------------------------------------------------------------------
# test_execution
# ---------------------------------------------------------------------------


class TestExecution:
    """Tests for TestClass.test_execution (fixture)."""

    def _call(self, submission, cases, verbosity=0):
        """Call the unwrapped test_execution fixture."""
        return HarnessClass.test_execution.__wrapped__(HarnessClass(), submission, cases, verbosity)

    def test_success_returns_case_and_result(self):
        """Successful execution returns (case, (outputs, kwargs, elapsed))."""

        def add(a, b):
            return a + b

        case = TestCase(inputs=((1, 2), {}), expected=((3,), {}))
        returned_case, result = self._call(add, case)
        assert returned_case is case
        pos, named, elapsed = result
        assert pos == (3,)
        assert named == {}
        assert isinstance(elapsed, float)

    def test_raises_true_forwards_exception(self):
        """When case.raises=True, exception is forwarded as the result."""

        def boom():
            raise ValueError("test error")

        case = TestCase(inputs=((), {}), expected=((), {}), raises=True)
        returned_case, result = self._call(boom, case)
        assert returned_case is case
        assert isinstance(result, ValueError)

    def test_raises_false_calls_pytest_fail(self):
        """When case.raises=False, unexpected exception triggers pytest.fail."""

        def boom():
            raise ValueError("unexpected")

        case = TestCase(inputs=((), {}), expected=((), {}), raises=False)
        with pytest.raises(pytest.fail.Exception):
            self._call(boom, case)


# ---------------------------------------------------------------------------
# test_assertion
# ---------------------------------------------------------------------------


class TestAssertion:
    """Tests for TestClass.test_assertion."""

    def test_ok_passes(self):
        """Assertion returning (OK, '') does not raise."""
        case = TestCase(inputs=((), {}), expected=((), {}))
        outputs = ((), {}, 0.1)

        def fn(case, outputs, *a, **kw):
            return (pytest.ExitCode.OK, "")

        assertions = (fn, ((), {}))
        HarnessClass().test_assertion((case, outputs), assertions, verbosity=0)

    def test_failure_calls_pytest_fail(self):
        """Assertion returning TESTS_FAILED triggers pytest.fail."""
        case = TestCase(inputs=((), {}), expected=((), {}))
        outputs = ((), {}, 0.1)

        def fn(case, outputs, *a, **kw):
            return (pytest.ExitCode.TESTS_FAILED, "wrong")

        assertions = (fn, ((), {}))
        with pytest.raises(pytest.fail.Exception):
            HarnessClass().test_assertion((case, outputs), assertions, verbosity=0)
