"""Tests for cases.py — Timer, format_result, execute dispatches."""

import dataclasses
import functools
import importlib.util
import logging
import sys

import numpy as np
import pytest

from pytest_nbgrader.cases import TestCase, TestSubtask, Timer, execute, format_result, raised_by_submission


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------


class TestTimer:
    """Tests for the Timer context manager."""

    def test_elapsed_positive(self):
        """Timer measures positive elapsed time."""
        with Timer() as t:
            _ = sum(range(100))
        assert t.elapsed > 0

    def test_start_and_end_set(self):
        """Timer sets start and end attributes."""
        with Timer() as t:
            pass
        assert t.start is not None
        assert t.end is not None
        assert t.end >= t.start

    def test_elapsed_before_exit(self):
        """Elapsed returns live time while still inside context."""
        with Timer() as t:
            mid = t.elapsed
        assert mid >= 0
        assert t.elapsed >= mid


# ---------------------------------------------------------------------------
# format_result
# ---------------------------------------------------------------------------


class TestFormatResult:
    """Tests for format_result log formatting."""

    def test_ok_result(self):
        """OK result includes 'passed' and the inputs."""
        msg = format_result(((1, 2), {}), pytest.ExitCode.OK)
        assert "passed" in msg
        assert "1" in msg
        assert "2" in msg

    def test_failed_result(self):
        """TESTS_FAILED includes 'failed' and the message."""
        msg = format_result(((3,), {}), pytest.ExitCode.TESTS_FAILED, message="wrong answer")
        assert "failed" in msg
        assert "wrong answer" in msg

    def test_internal_error(self):
        """INTERNAL_ERROR includes exception info."""
        msg = format_result(((), {}), pytest.ExitCode.INTERNAL_ERROR, exception="ZeroDivisionError")
        assert "could not be tested" in msg
        assert "ZeroDivisionError" in msg

    def test_unexpected_code(self):
        """Unknown exit code produces 'Unexpected result'."""
        msg = format_result(((), {}), "UNKNOWN_CODE")
        assert "Unexpected result" in msg

    def test_kwargs_formatting(self):
        """Keyword args formatted as key=value in output."""
        msg = format_result(((1,), {"x": 5}), pytest.ExitCode.OK)
        assert "x=5" in msg


# ---------------------------------------------------------------------------
# execute dispatches
# ---------------------------------------------------------------------------


class TestExecuteNotImplemented:
    """Test base dispatch raises NotImplementedError."""

    def test_unsupported_type(self):
        """Passing unsupported type raises NotImplementedError."""
        case = TestCase()
        with pytest.raises(NotImplementedError, match="Cannot run"):
            execute(42, case)

    def test_unsupported_type_list(self):
        """List is not a registered dispatch type."""
        case = TestCase()
        with pytest.raises(NotImplementedError):
            execute([1, 2, 3], case)


class TestExecuteFunction:
    """Tests for execute(FunctionType, case)."""

    def test_none_return(self):
        """Function returning None produces empty tuple."""

        def noop():
            pass

        case = TestCase(inputs=((), {}), expected=((), {}))
        args, kwargs, elapsed = execute(noop, case)
        assert args == ()
        assert elapsed > 0

    def test_single_return_wrapped(self):
        """Single return value wrapped in tuple when 1 expected."""

        def give_five():
            return 5

        case = TestCase(inputs=((), {}), expected=((5,), {}))
        args, _, _ = execute(give_five, case)
        assert args == (5,)

    def test_multiple_returns(self):
        """Multiple return values kept as tuple."""

        def pair():
            return 1, 2

        case = TestCase(inputs=((), {}), expected=((1, 2), {}))
        args, _, _ = execute(pair, case)
        assert args == (1, 2)

    def test_kwargs_passed(self):
        """Keyword arguments forwarded to function."""

        def greet(name="world"):
            return f"hello {name}"

        case = TestCase(inputs=((), {"name": "pytest"}), expected=(("hello pytest",), {}))
        args, _, _ = execute(greet, case)
        assert args == ("hello pytest",)

    def test_inputs_deepcopied(self):
        """Inputs are deepcopied — function can't mutate originals."""
        original_list = [1, 2, 3]

        def mutate(lst):
            lst.append(4)
            return lst

        case = TestCase(inputs=((original_list,), {}), expected=((None,), {}))
        execute(mutate, case)
        assert original_list == [1, 2, 3]

    def test_exception_propagates(self):
        """Function that raises propagates the exception through execute."""

        def failing():
            raise ValueError("boom")

        case = TestCase(inputs=((), {}), expected=((), {}), raises=True)
        with pytest.raises(ValueError, match="boom"):
            execute(failing, case)

    def test_output_count_mismatch_warning(self, caplog):
        """Mismatch between expected and actual output count logs warning."""

        def give_pair():
            return 1, 2

        # Expected 3 outputs but function returns 2 — triggers mismatch warning
        case = TestCase(inputs=((), {}), expected=((1, 2, 3), {}))
        with caplog.at_level(logging.WARNING):
            execute(give_pair, case)
        assert "Number of expected outputs" in caplog.text

    def test_output_count_mismatch_suppressed_when_raises(self, caplog):
        """Mismatch warning suppressed when case.raises is True."""

        def give_pair():
            return 1, 2

        case = TestCase(inputs=((), {}), expected=((1, 2, 3), {}), raises=True)
        with caplog.at_level(logging.WARNING):
            execute(give_pair, case)
        assert "Number of expected outputs" not in caplog.text


class TestExecuteCode:
    """Tests for execute(CodeType, case)."""

    def test_scope_variables(self):
        """Code execution produces named outputs from scope."""
        code = compile("z = x + y", "test", "exec")
        case = TestCase(inputs=((), {"x": 10, "y": 20}), expected=((), {"z": 30}))
        _, kwargs, _ = execute(code, case)
        assert kwargs["z"] == 30

    def test_scope_excludes_builtins(self):
        """Built-in scope entries (__builtins__) filtered out."""
        code = compile("a = 1", "test", "exec")
        case = TestCase(inputs=((), {}), expected=((), {"a": 1}))
        _, kwargs, _ = execute(code, case)
        assert "__builtins__" not in kwargs

    def test_input_scope_preserved(self):
        """Input variables that code doesn't overwrite still appear."""
        code = compile("b = x * 2", "test", "exec")
        case = TestCase(inputs=((), {"x": 5}), expected=((), {"x": 5, "b": 10}))
        _, kwargs, _ = execute(code, case)
        assert kwargs["x"] == 5
        assert kwargs["b"] == 10


class TestExecuteType:
    """Tests for execute(type, case) — class instantiation."""

    def test_single_instance(self):
        """Class instantiated once with given args."""

        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        case = TestCase(inputs=[((1, 2), {})])
        result, _, elapsed = execute(Point, case)
        assert len(result) == 1
        assert result[0].x == 1
        assert result[0].y == 2

    def test_multiple_instances(self):
        """Class instantiated multiple times from input list."""

        class Counter:
            def __init__(self, n):
                self.n = n

        case = TestCase(inputs=[((1,), {}), ((2,), {}), ((3,), {})])
        result, _, _ = execute(Counter, case)
        assert len(result) == 3
        assert [r.n for r in result] == [1, 2, 3]

    def test_kwargs_passed(self):
        """Keyword args forwarded to class constructor."""

        class Named:
            def __init__(self, name="default"):
                self.name = name

        case = TestCase(inputs=[((), {"name": "test"})])
        result, _, _ = execute(Named, case)
        assert result[0].name == "test"


class TestExecuteModuleSpec:
    """Tests for execute(ModuleSpec, case)."""

    def test_module_import(self, tmp_path):
        """Module loaded from spec and returned as positional output."""
        mod_file = tmp_path / "sample.py"
        mod_file.write_text("VALUE = 42\n")
        spec = importlib.util.spec_from_file_location("sample", mod_file)
        case = TestCase()
        result, _, elapsed = execute(spec, case)
        assert len(result) == 1
        assert result[0].VALUE == 42
        assert elapsed > 0

    def test_module_with_function(self, tmp_path):
        """Module with a function — function accessible on returned module."""
        mod_file = tmp_path / "funcs.py"
        mod_file.write_text("def add(a, b):\n    return a + b\n")
        spec = importlib.util.spec_from_file_location("funcs", mod_file)
        case = TestCase()
        result, _, _ = execute(spec, case)
        assert result[0].add(3, 4) == 7


# ---------------------------------------------------------------------------
# TestCase / TestSubtask dataclasses
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Tests for TestCase and TestSubtask defaults."""

    def test_testcase_defaults(self):
        """TestCase has sensible defaults."""
        tc = TestCase()
        assert tc.inputs == ((), {})
        assert tc.expected == ((), {})
        assert tc.raises is False
        assert tc.timing == (None, None)

    def test_testsubtask_defaults(self):
        """TestSubtask prerequisites default to empty dict."""
        ts = TestSubtask(cases=[], assertions={})
        assert ts.prerequisites == {}


# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------


class TestExecuteOutputShaping:
    """Return values are always normalised to a tuple of positional outputs."""

    @pytest.mark.parametrize(
        ("return_value", "expected_count", "outputs"),
        [
            (7, 2, (7,)),  # scalar where two outputs were expected
            (5, 0, (5,)),  # value where none was expected
            ("ab", 2, ("ab",)),  # strings are not split into characters
            ([1, 2], 2, (1, 2)),  # a list counts as multiple outputs
            ((1, 2), 2, (1, 2)),
            (None, 1, (None,)),  # None is a legitimate single output
            (None, 2, ()),
        ],
    )
    def test_shapes(self, return_value, expected_count, outputs):
        """Outputs are shaped without calling len() on arbitrary return values."""
        case = TestCase(inputs=((), {}), expected=((None,) * expected_count, {}))
        assert execute(lambda: return_value, case)[0] == outputs


class TestRaisedBySubmission:
    """Exceptions from student code are told apart from plugin errors."""

    def test_function_exception_is_tagged(self):
        """An exception raised by the student function is tagged."""

        def boom():
            raise ValueError("student")

        with pytest.raises(ValueError, match="student") as excinfo:
            execute(boom, TestCase())
        assert raised_by_submission(excinfo.value)

    def test_unsupported_submission_is_not_tagged(self):
        """The plugin's own NotImplementedError is not tagged."""
        with pytest.raises(NotImplementedError) as excinfo:
            execute(42, TestCase())
        assert not raised_by_submission(excinfo.value)

    def test_malformed_class_inputs_are_not_tagged(self):
        """Malformed class inputs are an instructor error, not the student's exception."""

        class Point:
            pass

        with pytest.raises(ValueError) as excinfo:
            execute(Point, TestCase())
        assert not raised_by_submission(excinfo.value)

    def test_class_constructor_exception_is_tagged(self):
        """An exception raised by the student's constructor is tagged."""

        class Broken:
            def __init__(self, x):
                raise RuntimeError(x)

        with pytest.raises(RuntimeError) as excinfo:
            execute(Broken, TestCase(inputs=[((1,), {})]))
        assert raised_by_submission(excinfo.value)

    def test_system_exit_is_tagged(self):
        """sys.exit() in student code is tagged like any other exception."""
        with pytest.raises(SystemExit) as excinfo:
            execute(compile("raise SystemExit(3)", "s", "exec"), TestCase())
        assert raised_by_submission(excinfo.value)


class TestExecuteCallables:
    """Callables other than plain functions can be graded."""

    def test_memoized_function(self):
        """functools.cache-decorated functions run like plain functions."""

        @functools.cache
        def fib(n):
            return n if n < 2 else fib(n - 1) + fib(n - 2)

        assert execute(fib, TestCase(inputs=((10,), {}), expected=((55,), {})))[0] == (55,)

    def test_partial(self):
        """functools.partial objects run like plain functions."""
        assert execute(functools.partial(pow, 2), TestCase(inputs=((3,), {}), expected=((8,), {})))[0] == (8,)

    def test_abc_class_is_instantiated(self):
        """Classes (even with a metaclass) are still instantiated, not called as functions."""

        class Meta(type):
            pass

        class Point(metaclass=Meta):
            def __init__(self, x):
                self.x = x

        (instance,), _, _ = execute(Point, TestCase(inputs=[((1,), {})]))
        assert instance.x == 1


class TestExecuteCodeRegressions:
    """Code strings run like notebook cells."""

    def test_runs_as_main(self):
        """``if __name__ == "__main__":`` blocks run, as they do in a notebook."""
        code = compile('if __name__ == "__main__":\n    result = 1', "s", "exec")
        assert execute(code, TestCase())[1] == {"result": 1}

    def test_dunder_names_are_not_outputs(self):
        """Annotations do not leak into the output scope."""
        code = compile("result: int = x + 1", "s", "exec")
        assert execute(code, TestCase(inputs=((), {"x": 1})))[1] == {"x": 1, "result": 2}


class TestExecuteClassRegressions:
    """Class inputs are isolated between executions."""

    def test_inputs_deepcopied(self):
        """A constructor mutating its argument does not change the test case."""

        class Stack:
            def __init__(self, items):
                items.append("sentinel")
                self.items = items

        case = TestCase(inputs=[(([1],), {})])
        execute(Stack, case)
        execute(Stack, case)
        assert case.inputs == [(([1],), {})]


class TestExecuteModuleSpecRegressions:
    """Modules are registered in sys.modules while they run."""

    def test_dataclass_with_postponed_annotations(self, tmp_path):
        """A module defining a dataclass under ``from __future__ import annotations`` imports."""
        path = tmp_path / "stud_dc.py"
        path.write_text(
            "from __future__ import annotations\nimport dataclasses\n\n@dataclasses.dataclass\nclass Point:\n    x: int\n\nP = Point(1)\n"
        )
        spec = importlib.util.spec_from_file_location("stud_dc", path)
        (module,), _, _ = execute(spec, TestCase())
        assert module.P.x == 1
        assert "stud_dc" not in sys.modules


class TestFormatResultShapes:
    """format_result handles every documented inputs shape."""

    @pytest.mark.parametrize(
        ("inputs", "formatted"),
        [
            ([((1, 2), {})], "1, 2"),  # one class instantiation
            ([((1, 2), {}), ((3,), {"y": 4})], "1, 2; 3, y=4"),  # several instantiations
            ([[1, 2], {}], "1, 2"),  # list-shaped function inputs (e.g. from hand-written YAML)
            ("garbage", "'garbage'"),
        ],
    )
    def test_shapes(self, inputs, formatted):
        """Inputs are formatted instead of raising IndexError/AttributeError."""
        assert f"\n{formatted}\n" in format_result(inputs, pytest.ExitCode.TESTS_FAILED, "msg")


class TestNotCollected:
    """The dataclasses are not mistaken for pytest test classes."""

    def test_dunder_test_false(self):
        """TestCase and TestSubtask opt out of pytest collection."""
        assert TestCase.__test__ is False
        assert TestSubtask.__test__ is False


class TestReviewRegressions:
    """Regressions found while reviewing the fixes above."""

    def test_array_return_is_several_outputs(self):
        """A 1-D array returned for several expected outputs holds one output per element."""
        case = TestCase(inputs=((), {}), expected=((2.0, 1.0), {}))
        assert execute(lambda: np.array([2.0, 1.0]), case)[0] == (2.0, 1.0)

    def test_array_return_is_one_output(self):
        """An array returned for one expected output stays one output."""
        case = TestCase(inputs=((), {}), expected=((None,), {}))
        (output,), _, _ = execute(lambda: np.array([2.0, 1.0]), case)
        assert isinstance(output, np.ndarray)

    def test_frozen_exception_is_forwarded(self):
        """Exceptions that forbid attribute assignment (frozen dataclasses) are tagged and propagate unchanged."""

        @dataclasses.dataclass(frozen=True)
        class InvalidInputError(Exception):
            value: int

        def check(x):
            raise InvalidInputError(x)

        with pytest.raises(InvalidInputError) as excinfo:
            execute(check, TestCase(inputs=((-1,), {})))
        assert raised_by_submission(excinfo.value)

    def test_frozen_exception_from_module(self, tmp_path):
        """A frozen exception raised while a module runs propagates unchanged."""
        path = tmp_path / "frozen_mod.py"
        path.write_text("import dataclasses\n\n@dataclasses.dataclass(frozen=True)\nclass E(Exception):\n    x: int\n\nraise E(1)\n")
        spec = importlib.util.spec_from_file_location("frozen_mod", path)
        with pytest.raises(Exception) as excinfo:  # the exception class is defined by the module
            execute(spec, TestCase())
        assert type(excinfo.value).__name__ == "E"
        assert raised_by_submission(excinfo.value)
