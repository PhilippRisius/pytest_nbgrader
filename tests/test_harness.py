"""Tests for harness.py — TestClass test methods."""

from unittest.mock import MagicMock

import pytest

from pytest_nbgrader.assertions import equal_value, raises
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

    def test_labelled_prerequisite(self):
        """The documented ``{"label": (function, (args, kwargs))}`` form is unpacked."""
        mock_fn = MagicMock(return_value=pytest.ExitCode.OK)
        HarnessClass().test_prerequisites("sub", ("signature", (mock_fn, (("ref",), {}))))
        mock_fn.assert_called_once_with("sub", "ref")


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

    def test_raises_false_verbose_includes_traceback(self):
        """Verbose mode includes the full traceback in the failure message."""

        def helper_inner():
            raise ValueError("detailed error")

        def boom():
            helper_inner()

        case = TestCase(inputs=((), {}), expected=((), {}), raises=False)
        with pytest.raises(pytest.fail.Exception, match="could not be tested") as excinfo:
            self._call(boom, case, verbosity=1)
        message = str(excinfo.value)
        assert "in boom" in message
        assert "in helper_inner" in message

    def test_quiet_shows_innermost_frame(self):
        """Without -v only the innermost frame (the student's failing line) is shown."""

        def helper_inner():
            raise ValueError("detailed error")

        def boom():
            helper_inner()

        case = TestCase(inputs=((), {}), expected=((), {}), raises=False)
        with pytest.raises(pytest.fail.Exception) as excinfo:
            self._call(boom, case, verbosity=0)
        message = str(excinfo.value)
        assert "in helper_inner" in message
        assert "in boom" not in message
        assert "During handling" not in message

    def test_raises_true_does_not_forward_plugin_errors(self):
        """With raises=True, errors of the plugin itself are not mistaken for the student's exception."""
        case = TestCase(inputs=((), {}), expected=((), {}), raises=True)
        with pytest.raises(pytest.fail.Exception, match="could not be tested"):
            self._call(42, case)  # no execute() implementation -> NotImplementedError

    def test_raises_true_non_raising_student_is_not_forwarded(self):
        """A student who returns a scalar instead of raising gets outputs, not a plugin TypeError."""
        case = TestCase(inputs=(("a",), {}), expected=((), {}), raises=True)
        _, result = self._call(lambda x: 0, case)
        assert result[0] == (0,)

    def test_system_exit_is_reported(self):
        """sys.exit() in student code fails the case instead of escaping the fixture."""

        def quits():
            raise SystemExit("negative input")

        case = TestCase(inputs=((), {}), expected=((), {}))
        with pytest.raises(pytest.fail.Exception, match="SystemExit"):
            self._call(quits, case)

    def test_system_exit_can_be_expected(self):
        """SystemExit can be tested with raises=True."""

        def quits():
            raise SystemExit(1)

        case = TestCase(inputs=((), {}), expected=((), {}), raises=True)
        _, result = self._call(quits, case)
        assert isinstance(result, SystemExit)

    def test_class_failure_message_is_formatted(self):
        """Constructor errors of class submissions are formatted instead of crashing format_result."""

        class Broken:
            def __init__(self, x):
                raise ValueError("student bug")

        case = TestCase(inputs=[((1,), {})], expected=((), {}))
        with pytest.raises(pytest.fail.Exception, match="could not be tested:\n1\n"):
            self._call(Broken, case)


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

    def test_assertion_exception_triggers_internal_error(self):
        """Assertion function raising an exception triggers pytest.fail with INTERNAL_ERROR."""
        case = TestCase(inputs=((), {}), expected=((), {}))
        outputs = ((), {}, 0.1)

        def fn(case, outputs, *a, **kw):
            raise RuntimeError("assertion crashed")

        assertions = (fn, ((), {}))
        with pytest.raises(pytest.fail.Exception, match="could not be tested"):
            HarnessClass().test_assertion((case, outputs), assertions, verbosity=0)

    def test_expected_exception_skips_value_assertions(self):
        """For raises=True cases, value assertions do not run on the exception."""
        case = TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True)
        HarnessClass().test_assertion((case, ZeroDivisionError()), (equal_value, ((), {})), verbosity=0)

    def test_expected_exception_checked_by_raises(self):
        """The raises assertion still checks the exception type."""
        case = TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True)
        HarnessClass().test_assertion((case, ZeroDivisionError()), (raises, ((ZeroDivisionError,), {})), verbosity=0)
        with pytest.raises(pytest.fail.Exception, match="Test case failed"):
            HarnessClass().test_assertion((case, ZeroDivisionError()), (raises, ((ValueError,), {})), verbosity=0)

    def test_labelled_assertion(self):
        """Assertions keyed by a label, ``{"label": (function, (args, kwargs))}``, are unpacked."""
        case = TestCase(inputs=((), {}), expected=((1,), {}))
        HarnessClass().test_assertion((case, ((1,), {}, 0.0)), ("value", (equal_value, ((), {}))), verbosity=0)
        with pytest.raises(pytest.fail.Exception, match="Test case failed"):
            HarnessClass().test_assertion((case, ((2,), {}, 0.0)), ("value", (equal_value, ((), {}))), verbosity=0)

    def test_class_inputs_failure_message(self):
        """Failures on class submissions show the assertion message, not a format_result crash."""
        case = TestCase(inputs=[((1, 2), {}), ((3, 4), {})], expected=((), {}))

        def fn(case, outputs, *a, **kw):
            return (pytest.ExitCode.TESTS_FAILED, "attribute differs")

        with pytest.raises(pytest.fail.Exception, match="1, 2; 3, 4") as excinfo:
            HarnessClass().test_assertion((case, ((), {}, 0.0)), (fn, ((), {})), verbosity=0)
        assert "attribute differs" in str(excinfo.value)


class TestReviewRegressions:
    """Regressions found while reviewing the fixes above."""

    def test_custom_assertion_receives_exception(self):
        """Assertions without accepts_exceptions = False receive the exception, as before."""
        case = TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True)
        received = []

        def check_message(case, outputs, *a, **kw):
            received.append(outputs)
            return (pytest.ExitCode.TESTS_FAILED, "expected a ValueError")

        with pytest.raises(pytest.fail.Exception, match="expected a ValueError"):
            HarnessClass().test_assertion((case, ZeroDivisionError("x")), (check_message, ((), {})), verbosity=0)
        assert isinstance(received[0], ZeroDivisionError)
