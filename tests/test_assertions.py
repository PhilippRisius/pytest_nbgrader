"""Tests for the assertions module."""

import pathlib

import numpy as np
import pytest

from pytest_nbgrader import assertions
from pytest_nbgrader.assertions import _log
from pytest_nbgrader.cases import TestCase


def make_case(inputs=None, expected=None, raises=False, timing=(None, None)):
    """Build a TestCase with sensible defaults."""
    return TestCase(
        inputs=inputs or ((), {}),
        expected=expected or ((), {}),
        raises=raises,
        timing=timing,
    )


class _Obj:
    """Simple object with arbitrary attributes for testing."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# _log decorator
# ---------------------------------------------------------------------------


class TestLog:
    """Tests for the _log decorator that wraps assertion functions."""

    def test_wraps_ok_result(self):
        """_log returns (OK, '') when inner function returns OK."""

        @_log
        def dummy(case, outputs, *args, **kwargs):
            return pytest.ExitCode.OK

        case = make_case()
        result, message = dummy(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.OK
        assert message == ""

    def test_wraps_failure_result(self):
        """_log returns (TESTS_FAILED, message) when inner returns failure tuple."""

        @_log
        def dummy(case, outputs, *args, **kwargs):
            return pytest.ExitCode.TESTS_FAILED, "expected_val", "actual_val"

        case = make_case()
        result, message = dummy(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED
        assert "failed" in message.lower()

    def test_preserves_function_name(self):
        """_log uses functools.wraps so __name__ is preserved."""

        @_log
        def my_assertion(case, outputs, *args, **kwargs):
            return pytest.ExitCode.OK

        assert my_assertion.__name__ == "my_assertion"


# ---------------------------------------------------------------------------
# equal_value
# ---------------------------------------------------------------------------


class TestEqualValue:
    """Tests for equal_value assertion."""

    def test_match(self):
        """Matching positional outputs return OK."""
        case = make_case(expected=((42,), {}))
        result, _ = assertions.equal_value(case, ((42,), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_mismatch(self):
        """Mismatched positional outputs return TESTS_FAILED."""
        case = make_case(expected=((42,), {}))
        result, _ = assertions.equal_value(case, ((99,), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_named_match(self):
        """Named kwargs compared via *args keys."""
        case = make_case(expected=((), {"x": 5}))
        result, _ = assertions.equal_value(case, ((), {"x": 5}, 0.1), "x")
        assert result is pytest.ExitCode.OK

    def test_named_mismatch(self):
        """Named kwargs differ."""
        case = make_case(expected=((), {"x": 5}))
        result, _ = assertions.equal_value(case, ((), {"x": 9}, 0.1), "x")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_none_vs_value(self):
        """Student returns None, expected was a value."""
        case = make_case(expected=((42,), {}))
        result, _ = assertions.equal_value(case, ((None,), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_multiple_positional(self):
        """Multiple positional values all match."""
        case = make_case(expected=((1, 2, 3), {}))
        result, _ = assertions.equal_value(case, ((1, 2, 3), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_extra_output(self):
        """Student returns more values than expected (zip_longest pads None)."""
        case = make_case(expected=((1,), {}))
        result, _ = assertions.equal_value(case, ((1, 2), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_fewer_outputs(self):
        """Student returns fewer values than expected."""
        case = make_case(expected=((1, 2), {}))
        result, _ = assertions.equal_value(case, ((1,), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_empty_outputs(self):
        """Student returns nothing, nothing expected — OK."""
        case = make_case(expected=((), {}))
        result, _ = assertions.equal_value(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_mixed_positional_and_named(self):
        """Both positional and named values checked together."""
        case = make_case(expected=((10,), {"y": 20}))
        result, _ = assertions.equal_value(case, ((10,), {"y": 20}, 0.1), "y")
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# almost_equal
# ---------------------------------------------------------------------------


class TestAlmostEqual:
    """Tests for almost_equal assertion."""

    def test_within_tolerance(self):
        """Values within default tolerance return OK."""
        case = make_case(expected=((1.0,), {}))
        result, _ = assertions.almost_equal(case, ((1.0 + 1e-8,), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_outside_tolerance(self):
        """Values outside tolerance return TESTS_FAILED."""
        case = make_case(expected=((1.0,), {}))
        result, _ = assertions.almost_equal(case, ((2.0,), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_custom_tolerance(self):
        """Custom atol allows larger differences."""
        case = make_case(expected=((1.0,), {}))
        result, _ = assertions.almost_equal(case, ((1.1,), {}, 0.1), atol=0.2)
        assert result is pytest.ExitCode.OK

    def test_type_fallback_equal(self):
        """Non-numeric types fall back to strict equality."""
        case = make_case(expected=(("hello",), {}))
        result, _ = assertions.almost_equal(case, (("hello",), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_type_fallback_mismatch(self):
        """Non-numeric types differ under strict fallback."""
        case = make_case(expected=(("hello",), {}))
        result, _ = assertions.almost_equal(case, (("world",), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_numpy_array(self):
        """Numpy arrays compared with allclose."""
        case = make_case(expected=((np.array([1.0, 2.0]),), {}))
        result, _ = assertions.almost_equal(case, ((np.array([1.0, 2.0 + 1e-9]),), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_numpy_array_outside(self):
        """Numpy arrays that differ beyond tolerance."""
        case = make_case(expected=((np.array([1.0, 2.0]),), {}))
        result, _ = assertions.almost_equal(case, ((np.array([1.0, 999.0]),), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_named_variable(self):
        """Named variable comparison via *args key."""
        case = make_case(expected=((), {"x": 1.0}))
        result, _ = assertions.almost_equal(case, ((), {"x": 1.0 + 1e-9}, 0.1), "x")
        assert result is pytest.ExitCode.OK

    def test_multiple_positional(self):
        """Multiple positional values all within tolerance."""
        case = make_case(expected=((1.0, 2.0), {}))
        result, _ = assertions.almost_equal(case, ((1.0 + 1e-9, 2.0 + 1e-9), {}, 0.1))
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# raises
# ---------------------------------------------------------------------------


class TestRaises:
    """Tests for raises assertion."""

    def test_correct_exception(self):
        """Expected exception type matches — OK."""
        case = make_case(raises=True)
        result, _ = assertions.raises(case, ValueError("oops"), ValueError)
        assert result is pytest.ExitCode.OK

    def test_wrong_exception(self):
        """Exception type does not match — TESTS_FAILED."""
        case = make_case(raises=True)
        result, _ = assertions.raises(case, TypeError("oops"), ValueError)
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_not_expected(self):
        """case.raises=False — no-op, always passes."""
        case = make_case(raises=False)
        result, _ = assertions.raises(case, ((42,), {}, 0.1), ValueError)
        assert result is pytest.ExitCode.OK

    def test_multiple_types(self):
        """Multiple acceptable exception types."""
        case = make_case(raises=True)
        result, _ = assertions.raises(case, TypeError("x"), ValueError, TypeError)
        assert result is pytest.ExitCode.OK

    def test_subclass_exception(self):
        """Subclass of expected exception (isinstance semantics)."""
        case = make_case(raises=True)

        class CustomError(ValueError):
            pass

        result, _ = assertions.raises(case, CustomError("x"), ValueError)
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# equal_types
# ---------------------------------------------------------------------------


class TestEqualTypes:
    """Tests for equal_types assertion."""

    def test_match(self):
        """Same types return OK."""
        case = make_case(expected=((), {"x": 42}))
        result, _ = assertions.equal_types(case, ((), {"x": 99}, 0.1), "x")
        assert result is pytest.ExitCode.OK

    def test_mismatch(self):
        """Different types return TESTS_FAILED."""
        case = make_case(expected=((), {"x": 42}))
        result, _ = assertions.equal_types(case, ((), {"x": "hello"}, 0.1), "x")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_bool_is_int(self):
        """Bool is subclass of int — isinstance check passes."""
        case = make_case(expected=((), {"x": 42}))
        result, _ = assertions.equal_types(case, ((), {"x": True}, 0.1), "x")
        assert result is pytest.ExitCode.OK

    def test_multiple_vars(self):
        """Multiple named variables all checked."""
        case = make_case(expected=((), {"x": 42, "y": "hello"}))
        result, _ = assertions.equal_types(case, ((), {"x": 99, "y": "world"}, 0.1), "x", "y")
        assert result is pytest.ExitCode.OK

    def test_one_of_many_wrong(self):
        """One variable has wrong type among several."""
        case = make_case(expected=((), {"x": 42, "y": "hello"}))
        result, _ = assertions.equal_types(case, ((), {"x": 99, "y": 123}, 0.1), "x", "y")
        assert result is pytest.ExitCode.TESTS_FAILED


# ---------------------------------------------------------------------------
# equal_scope
# ---------------------------------------------------------------------------


class TestEqualScope:
    """Tests for equal_scope assertion."""

    def test_match(self):
        """Same variable names return OK."""
        case = make_case(expected=((), {"x": 1, "y": 2}))
        result, _ = assertions.equal_scope(case, ((), {"x": 1, "y": 2}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_missing_var(self):
        """Student missing a variable returns TESTS_FAILED."""
        case = make_case(expected=((), {"x": 1, "y": 2}))
        result, _ = assertions.equal_scope(case, ((), {"x": 1}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_extra_var(self):
        """Student has extra variable returns TESTS_FAILED."""
        case = make_case(expected=((), {"x": 1}))
        result, _ = assertions.equal_scope(case, ((), {"x": 1, "z": 3}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_empty_scope(self):
        """Both scopes empty — OK."""
        case = make_case(expected=((), {}))
        result, _ = assertions.equal_scope(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_values_differ_but_names_match(self):
        """Values differ but scope only checks names — OK."""
        case = make_case(expected=((), {"x": 1}))
        result, _ = assertions.equal_scope(case, ((), {"x": 999}, 0.1))
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# time_bounds
# ---------------------------------------------------------------------------


class TestTimeBounds:
    """Tests for time_bounds assertion."""

    def test_within_bounds(self):
        """Time within (lower, upper) returns OK."""
        case = make_case(timing=(0.0, 1.0))
        result, _ = assertions.time_bounds(case, ((), {}, 0.5))
        assert result is pytest.ExitCode.OK

    def test_too_slow(self):
        """Time above upper bound returns TESTS_FAILED."""
        case = make_case(timing=(0.0, 0.1))
        result, _ = assertions.time_bounds(case, ((), {}, 0.5))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_too_fast(self):
        """Time below lower bound returns TESTS_FAILED."""
        case = make_case(timing=(1.0, 2.0))
        result, _ = assertions.time_bounds(case, ((), {}, 0.5))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_none_upper(self):
        """Upper=None uses 2*time fallback — always passes."""
        case = make_case(timing=(0.0, None))
        result, _ = assertions.time_bounds(case, ((), {}, 0.5))
        assert result is pytest.ExitCode.OK

    def test_none_lower(self):
        """Lower=None uses 0 fallback."""
        case = make_case(timing=(None, 1.0))
        result, _ = assertions.time_bounds(case, ((), {}, 0.5))
        assert result is pytest.ExitCode.OK

    def test_both_none(self):
        """Both bounds None — always passes."""
        case = make_case(timing=(None, None))
        result, _ = assertions.time_bounds(case, ((), {}, 0.5))
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# close_attributes
# ---------------------------------------------------------------------------


class TestCloseAttributes:
    """Tests for close_attributes assertion."""

    def test_match(self):
        """Attributes within tolerance return OK."""
        case = make_case()
        case.expected = _Obj(x=1.0, y=2.0)
        outputs = _Obj(x=1.0 + 1e-9, y=2.0 + 1e-9)
        result, _ = assertions.close_attributes(case, outputs, "x", "y")
        assert result is pytest.ExitCode.OK

    def test_outside(self):
        """Attributes outside tolerance return TESTS_FAILED."""
        case = make_case()
        case.expected = _Obj(x=1.0)
        outputs = _Obj(x=999.0)
        result, _ = assertions.close_attributes(case, outputs, "x")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_multiple_attrs_one_bad(self):
        """One attribute out of several is off — TESTS_FAILED."""
        case = make_case()
        case.expected = _Obj(x=1.0, y=2.0)
        outputs = _Obj(x=1.0, y=999.0)
        result, _ = assertions.close_attributes(case, outputs, "x", "y")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_numpy_array_attributes(self):
        """Numpy array attributes compared within tolerance."""
        case = make_case()
        case.expected = _Obj(data=np.array([1.0, 2.0, 3.0]))
        outputs = _Obj(data=np.array([1.0, 2.0 + 1e-9, 3.0]))
        result, _ = assertions.close_attributes(case, outputs, "data")
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# equal_contents
# ---------------------------------------------------------------------------


class TestEqualContents:
    """Tests for equal_contents assertion."""

    def test_kwargs_match(self):
        """Named container contents match — OK."""
        case = make_case(expected=((), {"data": [1, 2, 3]}))
        result, _ = assertions.equal_contents(case, ((), {"data": [1, 2, 3]}, 0.1), "data")
        assert result is pytest.ExitCode.OK

    def test_kwargs_mismatch(self):
        """Named container contents differ — TESTS_FAILED."""
        case = make_case(expected=((), {"data": [1, 2, 3]}))
        result, _ = assertions.equal_contents(case, ((), {"data": [1, 2, 9]}, 0.1), "data")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_positional_mismatch(self):
        """Positional container contents differ — TESTS_FAILED."""
        case = make_case(expected=((42,), {}))
        result, _ = assertions.equal_contents(case, ((99,), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_empty_containers(self):
        """Empty containers — OK."""
        case = make_case(expected=((), {"data": []}))
        result, _ = assertions.equal_contents(case, ((), {"data": []}, 0.1), "data")
        assert result is pytest.ExitCode.OK

    def test_multiple_named_containers(self):
        """Multiple named containers all match."""
        case = make_case(expected=((), {"a": [1], "b": [2]}))
        result, _ = assertions.equal_contents(case, ((), {"a": [1], "b": [2]}, 0.1), "a", "b")
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# file_contents
# ---------------------------------------------------------------------------


class TestFileContents:
    """Tests for file_contents assertion."""

    def test_match(self, tmp_path):
        """File has expected binary contents — OK."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello")
        case = make_case(expected=((), {str(test_file): b"hello"}))
        result, _ = assertions.file_contents(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_mismatch(self, tmp_path):
        """File has different binary contents — TESTS_FAILED."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello")
        case = make_case(expected=((), {str(test_file): b"world"}))
        result, _ = assertions.file_contents(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_multiple_files(self, tmp_path):
        """Multiple files all match."""
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        case = make_case(expected=((), {str(f1): b"aaa", str(f2): b"bbb"}))
        result, _ = assertions.file_contents(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.OK

    def test_empty_file(self, tmp_path):
        """Empty file matches empty expected contents."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")
        case = make_case(expected=((), {str(test_file): b""}))
        result, _ = assertions.file_contents(case, ((), {}, 0.1))
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# has_import — uses case.return_object (dynamic attribute)
# Note: has_import has @_log but its inner function signature is
# (case, *args, **kwargs), so `outputs` from the wrapper gets swept
# into *args. We test the inner function directly via __wrapped__.
# ---------------------------------------------------------------------------


class TestHasImport:
    """
    Tests for has_import assertion.

    has_import uses inspect.getmodule() to determine where objects come from.
    It has several known issues (relative_to(cwd) crashes for stdlib modules,
    outputs parameter not handled, inconsistent return tuples). We test via
    __wrapped__ to bypass the _log wrapper's outputs injection.

    Tests use objects with no __module__ (getmodule returns None) to simulate
    the "locally defined" case, and project-local imports for the "imported" case.
    """

    def test_locally_defined_no_module(self):
        """Object with no discoverable module — expected=None passes."""
        # Create a class with __module__ pointing to nonexistent module
        # so inspect.getmodule() returns None
        obj = type("Foo", (), {})
        obj.__module__ = "_nonexistent_test_module_"

        case = make_case()
        case.return_object = _Obj(Foo=obj)
        result = assertions.has_import.__wrapped__(case, Foo=None)
        assert result is pytest.ExitCode.OK

    def test_locally_defined_but_expected_imported(self):
        """Object has no module but expected from a path — fails."""
        obj = type("Foo", (), {})
        obj.__module__ = "_nonexistent_test_module_"

        case = make_case()
        case.return_object = _Obj(Foo=obj)
        result = assertions.has_import.__wrapped__(case, Foo=pathlib.Path("some_module.py"))
        assert result is not pytest.ExitCode.OK

    def test_imported_but_expected_local(self):
        """Object from a real module but expected=None — fails."""
        case = make_case()
        # TestCase is from pytest_nbgrader.cases (project-local, under CWD)
        case.return_object = _Obj(TC=TestCase)
        result = assertions.has_import.__wrapped__(case, TC=None)
        assert result is not pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# equal_attributes (FIXED: was inverted, now normalized with @_log)
# ---------------------------------------------------------------------------


class TestEqualAttributes:
    """Tests for equal_attributes — previously had inverted logic."""

    def test_matching_attributes_ok(self):
        """When all attributes match, returns OK (was TESTS_FAILED before fix)."""
        expected_obj = _Obj(x=1, y=2)
        return_obj = _Obj(x=1, y=2)
        case = make_case(expected=((expected_obj,), {}))
        outputs = ((return_obj,), {}, 0.1)
        result, _ = assertions.equal_attributes(case, outputs, "x", "y")
        assert result is pytest.ExitCode.OK

    def test_mismatched_attributes_fails(self):
        """When attributes differ, returns TESTS_FAILED."""
        expected_obj = _Obj(x=1, y=2)
        return_obj = _Obj(x=1, y=99)
        case = make_case(expected=((expected_obj,), {}))
        outputs = ((return_obj,), {}, 0.1)
        result, _ = assertions.equal_attributes(case, outputs, "x", "y")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_returns_log_tuple(self):
        """Verify @_log wrapper returns (result, message) tuple."""
        expected_obj = _Obj(x=1)
        return_obj = _Obj(x=1)
        case = make_case(expected=((expected_obj,), {}))
        outputs = ((return_obj,), {}, 0.1)
        ret = assertions.equal_attributes(case, outputs, "x")
        assert isinstance(ret, tuple)
        assert len(ret) == 2

    def test_no_return_object(self):
        """Student returned nothing — empty positional outputs."""
        case = make_case(expected=((_Obj(x=1),), {}))
        outputs = ((), {}, 0.1)
        result, _ = assertions.equal_attributes(case, outputs, "x")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_missing_attribute_on_return(self):
        """Student object lacks an expected attribute."""
        expected_obj = _Obj(x=1, y=2)
        return_obj = _Obj(x=1)  # missing y
        case = make_case(expected=((expected_obj,), {}))
        outputs = ((return_obj,), {}, 0.1)
        result, _ = assertions.equal_attributes(case, outputs, "x", "y")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_single_attribute(self):
        """Single attribute comparison."""
        expected_obj = _Obj(name="test")
        return_obj = _Obj(name="test")
        case = make_case(expected=((expected_obj,), {}))
        outputs = ((return_obj,), {}, 0.1)
        result, _ = assertions.equal_attributes(case, outputs, "name")
        assert result is pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# has_method (FIXED: normalized with @_log, uses outputs)
# ---------------------------------------------------------------------------


class TestHasMethod:
    """Tests for has_method assertion."""

    def test_method_present(self):
        """Object has the required method."""

        class MyClass:
            def foo(self):
                pass

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, "foo")
        assert result is pytest.ExitCode.OK

    def test_method_missing(self):
        """Object lacks the required method."""

        class MyClass:
            pass

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, "foo")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_multiple_methods(self):
        """Object has multiple required methods."""

        class MyClass:
            def foo(self):
                pass

            def bar(self):
                pass

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, "foo", "bar")
        assert result is pytest.ExitCode.OK

    def test_one_of_many_missing(self):
        """Object has some but not all required methods."""

        class MyClass:
            def foo(self):
                pass

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, "foo", "bar")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_type_hint_check(self):
        """Attribute exists but has wrong type."""

        class MyClass:
            x = "not_an_int"

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, x=int)
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_type_hint_correct(self):
        """Attribute exists with correct type."""

        class MyClass:
            x = 42

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, x=int)
        assert result is pytest.ExitCode.OK

    def test_no_return_object(self):
        """Student returned nothing."""
        case = make_case()
        outputs = ((), {}, 0.1)
        result, _ = assertions.has_method(case, outputs, "foo")
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_returns_log_tuple(self):
        """Verify @_log wrapper returns (result, message) tuple."""

        class MyClass:
            def foo(self):
                pass

        case = make_case()
        outputs = ((MyClass(),), {}, 0.1)
        ret = assertions.has_method(case, outputs, "foo")
        assert isinstance(ret, tuple)
        assert len(ret) == 2


# ---------------------------------------------------------------------------
# calls (FIXED: normalized with @_log, uses outputs)
# ---------------------------------------------------------------------------


class TestCalls:
    """Tests for calls assertion."""

    def test_correct_call_sequence(self):
        """Function calls expected callee with expected args."""

        class MyModule:
            @staticmethod
            def helper(x):
                return x + 1

            @staticmethod
            def main():
                MyModule.helper(42)

        case = make_case()
        outputs = ((MyModule,), {}, 0.1)
        result, _ = assertions.calls(case, outputs, "main", helper=[((42,), {})])
        assert result is pytest.ExitCode.OK

    def test_wrong_arguments(self):
        """Callee called with wrong args."""

        class MyModule:
            @staticmethod
            def helper(x):
                return x + 1

            @staticmethod
            def main():
                MyModule.helper(99)

        case = make_case()
        outputs = ((MyModule,), {}, 0.1)
        result, _ = assertions.calls(case, outputs, "main", helper=[((42,), {})])
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_no_return_object(self):
        """Student returned nothing."""
        case = make_case()
        outputs = ((), {}, 0.1)
        result, _ = assertions.calls(case, outputs, "main", helper=[])
        assert result is pytest.ExitCode.TESTS_FAILED

    def test_not_a_type_or_module(self):
        """Return object is not a type or module."""
        case = make_case()
        outputs = (("just a string",), {}, 0.1)
        result, _ = assertions.calls(case, outputs, "main", helper=[])
        assert result is pytest.ExitCode.TESTS_FAILED
