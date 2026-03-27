"""Tests for cases.py — Timer, format_result, execute dispatches."""

import importlib.util

import pytest

from pytest_nbgrader.cases import TestCase, TestSubtask, Timer, execute, format_result


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
