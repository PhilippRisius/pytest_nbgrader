"""End-to-end tests: full instructor workflow submit → execute → assert."""

import inspect

import pytest
import yaml

from pytest_nbgrader.assertions import (
    almost_equal,
    equal_scope,
    equal_value,
    raises,
)
from pytest_nbgrader.cases import TestCase, TestSubtask, execute
from pytest_nbgrader.dumper import dump_subtask
from pytest_nbgrader.harness import TestClass as HarnessClass
from pytest_nbgrader.loader import Submission
from pytest_nbgrader.prerequisites import has_signature


# ---------------------------------------------------------------------------
# Function submission: submit → execute → equal_value
# ---------------------------------------------------------------------------


class TestFunctionWorkflow:
    """Full workflow for function submissions."""

    def test_correct_function_passes(self):
        """Correct function passes equal_value assertion end-to-end."""

        def add(a, b):
            return a + b

        Submission.submit(add)
        case = TestCase(inputs=((2, 3), {}), expected=((5,), {}))
        outputs = execute(Submission.submission, case)
        result, message = equal_value(case, outputs)
        assert result is pytest.ExitCode.OK

    def test_wrong_function_fails(self):
        """Wrong function triggers TESTS_FAILED through equal_value."""

        def add(a, b):
            return a + b + 1  # deliberately wrong

        Submission.submit(add)
        case = TestCase(inputs=((2, 3), {}), expected=((5,), {}))
        outputs = execute(Submission.submission, case)
        result, message = equal_value(case, outputs)
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_prerequisite_then_execute_then_assert(self):
        """Full pipeline: prerequisite check, execution, assertion."""

        def multiply(a, b):
            return a * b

        Submission.submit(multiply)
        case = TestCase(inputs=((3, 4), {}), expected=((12,), {}))

        # Prerequisite: function has correct signature
        ref_sig = inspect.signature(lambda a, b: None)
        prereq_result = has_signature(Submission.submission, ref_sig)
        assert prereq_result is pytest.ExitCode.OK

        # Execute
        outputs = execute(Submission.submission, case)
        assert outputs[0] == (12,)

        # Assert
        result, message = equal_value(case, outputs)
        assert result is pytest.ExitCode.OK

    def test_almost_equal_with_floats(self):
        """Near-equality assertion works for floating-point results."""

        def divide(a, b):
            return a / b

        Submission.submit(divide)
        case = TestCase(inputs=((1, 3), {}), expected=((0.3333333,), {}))
        outputs = execute(Submission.submission, case)
        result, message = almost_equal(case, outputs)
        assert result is pytest.ExitCode.OK

    def test_raises_assertion_for_expected_exception(self):
        """Raises assertion verifies expected exceptions."""

        def strict_div(a, b):
            if b == 0:
                raise ZeroDivisionError("no zero")
            return a / b

        Submission.submit(strict_div)
        case = TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True)

        # Execute — raises flag means exception is captured, not re-raised
        try:
            outputs = execute(Submission.submission, case)
        except ZeroDivisionError:
            outputs = ZeroDivisionError("no zero")

        result, message = raises(case, outputs, ZeroDivisionError)
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# Code string submission: submit → execute → equal_scope + equal_value
# ---------------------------------------------------------------------------


class TestCodeStringWorkflow:
    """Full workflow for code string (bytecode) submissions."""

    def test_bytecode_scope_and_values(self):
        """Code string execution populates scope, assertions pass."""
        code = "result = x + y"
        Submission.submit(code)
        # Bytecode execution keeps input vars in scope, so expected must include them
        case = TestCase(
            inputs=((), {"x": 10, "y": 20}),
            expected=((), {"x": 10, "y": 20, "result": 30}),
        )
        outputs = execute(Submission.submission, case)

        # Check scope — all vars (inputs + computed) match
        result_scope, msg_scope = equal_scope(case, outputs)
        assert result_scope is pytest.ExitCode.OK

        # Check values
        result_val, msg_val = equal_value(case, outputs)
        assert result_val is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# Class submission: submit → execute → assertions
# ---------------------------------------------------------------------------


class TestClassWorkflow:
    """Full workflow for class submissions."""

    def test_class_instantiation(self):
        """Class submission instantiates with execute(type, case)."""

        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        Submission.submit(Point)
        # Class dispatch expects inputs as list of (args, kwargs) pairs
        case = TestCase(inputs=[((1, 2), {}), ((3, 4), {})], expected=((), {}))
        outputs = execute(Submission.submission, case)
        assert len(outputs[0]) == 2
        assert outputs[0][0].x == 1
        assert outputs[0][1].y == 4


# ---------------------------------------------------------------------------
# Path submission: submit → execute → assertions
# ---------------------------------------------------------------------------


class TestPathWorkflow:
    """Full workflow for Path (module file) submissions."""

    def test_module_path_loads_and_executes(self, tmp_path):
        """Path submission loads module spec, executes it."""
        mod_file = tmp_path / "student.py"
        mod_file.write_text("answer = 42\ndef greet(): return 'hello'\n")
        Submission.submit(mod_file)

        case = TestCase(inputs=((), {}), expected=((), {}))
        outputs = execute(Submission.submission, case)

        # ModuleSpec execute returns the loaded module as outputs[0][0]
        module = outputs[0][0]
        assert module.answer == 42
        assert module.greet() == "hello"


# ---------------------------------------------------------------------------
# YAML round-trip: dump → load → execute → assert
# ---------------------------------------------------------------------------


class TestYamlWorkflow:
    """Dump test cases to YAML, load, then run full pipeline."""

    def test_yaml_roundtrip_then_execute(self, tmp_path):
        """Dump subtask to YAML, reload, execute test cases from it."""

        def square(x):
            return x * x

        Submission.submit(square)

        subtask = TestSubtask(
            cases=[
                TestCase(inputs=((2,), {}), expected=((4,), {})),
                TestCase(inputs=((5,), {}), expected=((25,), {})),
                TestCase(inputs=((-3,), {}), expected=((9,), {})),
            ],
            assertions={"eq": ("equal_value", ((), {}))},
        )

        yml = tmp_path / "subtask.yml"
        dump_subtask(subtask, to=yml)

        with yml.open("rb") as f:
            loaded = yaml.unsafe_load(f)

        assert isinstance(loaded, TestSubtask)

        for case in loaded.cases:
            outputs = execute(Submission.submission, case)
            result, message = equal_value(case, outputs)
            assert result is pytest.ExitCode.OK, f"Failed for {case.inputs}"


# ---------------------------------------------------------------------------
# Harness integration: test through TestClass methods
# ---------------------------------------------------------------------------


class TestHarnessWorkflow:
    """Test through HarnessClass methods like a real pytest run would."""

    def test_full_harness_pass(self):
        """Correct submission passes prerequisites + execution + assertion."""

        def add(a, b):
            return a + b

        Submission.submit(add)
        case = TestCase(inputs=((1, 2), {}), expected=((3,), {}))

        # Prerequisites
        def prereq_ok(sub, *a, **kw):
            return sub and pytest.ExitCode.OK

        HarnessClass().test_prerequisites(add, (prereq_ok, ((), {})))

        # Execution (through __wrapped__)
        tc, result = HarnessClass.test_execution.__wrapped__(HarnessClass(), add, case, verbosity=0)
        assert tc is case
        assert result[0] == (3,)

        # Assertion
        def assert_ok(case, outputs, *a, **kw):
            return (pytest.ExitCode.OK, "")

        HarnessClass().test_assertion((tc, result), (assert_ok, ((), {})), verbosity=0)

    def test_full_harness_fail(self):
        """Wrong submission fails at assertion stage through harness."""

        def add(a, b):
            return a + b + 999  # wrong

        Submission.submit(add)
        case = TestCase(inputs=((1, 2), {}), expected=((3,), {}))

        tc, result = HarnessClass.test_execution.__wrapped__(HarnessClass(), add, case, verbosity=0)

        def assert_fail(case, outputs, *a, **kw):
            return (pytest.ExitCode.TESTS_FAILED, "wrong answer")

        with pytest.raises(pytest.fail.Exception):
            HarnessClass().test_assertion((tc, result), (assert_fail, ((), {})), verbosity=0)
