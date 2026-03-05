"""Integration tests for pytest_nbgrader plugin machinery."""

import pathlib
import types

import yaml

from pytest_nbgrader.cases import TestCase, TestSubtask, execute
from pytest_nbgrader.dumper import dump_subtask
from pytest_nbgrader.loader import Submission


class TestSubmission:
    """Test the Submission loader with different input types."""

    def test_submit_function(self):
        """Submit a plain function via Submission.submit()."""

        def add(a, b):
            return a + b

        Submission.submit(add)
        assert Submission.submission is add

    def test_submit_string(self):
        """Submit a code string — compiles to bytecode."""
        code = "x = 1 + 2"
        Submission.submit(code)
        assert isinstance(Submission.submission, types.CodeType)

    def test_submit_class(self):
        """Submit a class."""

        class MyClass:
            value = 42

        Submission.submit(MyClass)
        assert Submission.submission is MyClass

    def test_submission_storage(self):
        """Submission.submission stores the last submitted object."""
        Submission.submission = "test_value"
        assert Submission.submission == "test_value"
        Submission.submission = None


class TestExecuteFunction:
    """Test execute() singledispatch with function submissions."""

    def test_execute_function_returns_value(self):
        """Execute a function and verify outputs."""

        def multiply(a, b):
            return a * b

        case = TestCase(
            inputs=((3, 4), {}),
            expected=((12,), {}),
        )
        output_args, output_kwargs, elapsed = execute(multiply, case)
        assert output_args == (12,)
        assert elapsed > 0

    def test_execute_function_multiple_returns(self):
        """Execute a function returning multiple values."""

        def divmod_func(a, b):
            return a // b, a % b

        case = TestCase(
            inputs=((17, 5), {}),
            expected=((3, 2), {}),
        )
        output_args, output_kwargs, elapsed = execute(divmod_func, case)
        assert output_args == (3, 2)

    def test_execute_code_object(self):
        """Execute compiled bytecode."""
        code = compile("result = x + y", "test", "exec")
        case = TestCase(
            inputs=((), {"x": 10, "y": 20}),
            expected=((), {"result": 30}),
        )
        output_args, output_kwargs, elapsed = execute(code, case)
        assert output_kwargs["result"] == 30


class TestYamlRoundTrip:
    """Test YAML serialization of test cases."""

    def test_dump_and_load_subtask(self, tmp_path):
        """Dump a TestSubtask to YAML and load it back."""
        cases = [
            TestCase(inputs=((1, 2), {}), expected=((3,), {})),
            TestCase(inputs=((0, 0), {}), expected=((0,), {})),
        ]
        subtask = TestSubtask(
            cases=cases,
            assertions={"function": "equal_value", "args": ((), {})},
        )

        yaml_file = tmp_path / "test_subtask.yml"
        dump_subtask(subtask, to=yaml_file)

        with pathlib.Path(yaml_file).open("rb") as f:
            loaded = yaml.unsafe_load(f)

        assert isinstance(loaded, TestSubtask)
        assert len(loaded.cases) == 2
        assert loaded.cases[0].inputs == ((1, 2), {})
        assert loaded.cases[0].expected == ((3,), {})


class TestPluginRegistration:
    """Test that the plugin registers correctly with pytest."""

    def test_plugin_is_registered(self):
        """Verify conftest hooks are discoverable."""
        from pytest_nbgrader import conftest

        assert hasattr(conftest, "pytest_addoption")
        assert hasattr(conftest, "pytest_generate_tests")
        assert hasattr(conftest, "pytest_sessionstart")
        assert hasattr(conftest, "pytest_sessionfinish")

    def test_submission_fixture_exists(self):
        """Verify the submission fixture function exists."""
        from pytest_nbgrader.conftest import submission

        assert callable(submission)

    def test_verbosity_fixture_exists(self):
        """Verify the verbosity fixture function exists."""
        from pytest_nbgrader.conftest import verbosity

        assert callable(verbosity)
