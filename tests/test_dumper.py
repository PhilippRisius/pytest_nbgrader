"""Tests for dumper.py — dump_exercise, dump_task, dump_subtask append mode."""

import functools
import pathlib

import pytest
import yaml

from pytest_nbgrader.assertions import equal_value
from pytest_nbgrader.cases import TestCase, TestSubtask
from pytest_nbgrader.dumper import dump_exercise, dump_subtask, dump_task


def _make_subtask(**kwargs):
    """Create a minimal TestSubtask for testing."""
    defaults = {
        "cases": [TestCase(inputs=((1,), {}), expected=((1,), {}))],
        "assertions": {"function": "equal_value"},
    }
    defaults.update(kwargs)
    return TestSubtask(**defaults)


class TestDumpSubtask:
    """Tests for dump_subtask (partially covered by test_integration)."""

    def test_append_mode_adds_data(self, tmp_path):
        """Append mode should add to existing file, not truncate."""
        yaml_file = tmp_path / "test.yml"

        subtask1 = _make_subtask(cases=[TestCase(inputs=((1,), {}), expected=((1,), {}))])
        subtask2 = _make_subtask(cases=[TestCase(inputs=((2,), {}), expected=((2,), {}))])

        dump_subtask(subtask1, to=yaml_file, append=False)
        size_after_first = yaml_file.stat().st_size

        dump_subtask(subtask2, to=yaml_file, append=True)
        size_after_second = yaml_file.stat().st_size

        assert size_after_second > size_after_first

    def test_append_mode_both_subtasks_in_file(self, tmp_path):
        """Appending merges both subtasks into a single loadable subtask."""
        yaml_file = tmp_path / "test.yml"

        subtask1 = _make_subtask(cases=[TestCase(inputs=((111,), {}), expected=((111,), {}))])
        subtask2 = _make_subtask(cases=[TestCase(inputs=((222,), {}), expected=((222,), {}))])

        dump_subtask(subtask1, to=yaml_file, append=False)
        dump_subtask(subtask2, to=yaml_file, append=True)

        with yaml_file.open("rb") as f:
            loaded = yaml.unsafe_load(f)
        assert [case.inputs for case in loaded.cases] == [((111,), {}), ((222,), {})]

    def test_creates_parent_dirs(self, tmp_path):
        """dump_subtask creates parent directories if needed."""
        yaml_file = tmp_path / "deep" / "nested" / "test.yml"
        dump_subtask(_make_subtask(), to=yaml_file)
        assert yaml_file.exists()


class TestDumpTask:
    """Tests for dump_task."""

    def test_creates_directory(self, tmp_path):
        """dump_task creates the target directory."""
        task_dir = tmp_path / "task1"
        subtasks = {"sub_a": _make_subtask(), "sub_b": _make_subtask()}
        dump_task(subtasks, to=task_dir)
        assert task_dir.is_dir()

    def test_creates_yaml_per_subtask(self, tmp_path):
        """Each subtask gets its own YAML file."""
        task_dir = tmp_path / "task1"
        subtasks = {"sub_a": _make_subtask(), "sub_b": _make_subtask()}
        dump_task(subtasks, to=task_dir)
        assert (task_dir / "sub_a.yml").exists()
        assert (task_dir / "sub_b.yml").exists()

    def test_yaml_loadable(self, tmp_path):
        """Dumped YAML files can be loaded back."""
        task_dir = tmp_path / "task1"
        subtask = _make_subtask()
        dump_task({"check": subtask}, to=task_dir)
        with (task_dir / "check.yml").open("rb") as f:
            loaded = yaml.unsafe_load(f)
        assert isinstance(loaded, TestSubtask)


class TestDumpExercise:
    """Tests for dump_exercise."""

    def test_creates_task_subdirectories(self, tmp_path):
        """dump_exercise creates a subdirectory per task."""
        exercise = {
            "task1": {"sub_a": _make_subtask()},
            "task2": {"sub_b": _make_subtask()},
        }
        dump_exercise(exercise, to=tmp_path)
        assert (tmp_path / "task1").is_dir()
        assert (tmp_path / "task2").is_dir()

    def test_full_hierarchy(self, tmp_path):
        """Exercise → task → subtask.yml hierarchy created correctly."""
        exercise = {
            "task1": {"check_value": _make_subtask(), "check_type": _make_subtask()},
        }
        dump_exercise(exercise, to=tmp_path)
        assert (tmp_path / "task1" / "check_value.yml").exists()
        assert (tmp_path / "task1" / "check_type.yml").exists()

    def test_empty_exercise(self, tmp_path):
        """Empty exercise creates just the root directory."""
        dump_exercise({}, to=tmp_path / "empty")
        assert (tmp_path / "empty").is_dir()


class TestDumpRegressions:
    """Serialization details that affect grading."""

    def test_dict_order_preserved(self, tmp_path):
        """Dict inputs keep their insertion order (keys are not sorted)."""
        case = TestCase(inputs=(({"the": 3, "quick": 1, "brown": 1},), {"width": 3, "height": 4}), expected=((["the", "quick", "brown"],), {}))
        dump_subtask(_make_subtask(cases=[case]), to=tmp_path / "order.yml")
        with (tmp_path / "order.yml").open("rb") as f:
            (loaded,) = yaml.unsafe_load(f).cases
        assert list(loaded.inputs[0][0]) == ["the", "quick", "brown"]
        assert list(loaded.inputs[1]) == ["width", "height"]

    def test_str_paths(self, tmp_path):
        """Target paths may be strings."""
        dump_exercise({"task": {"sub": _make_subtask()}}, to=str(tmp_path / "tests"))
        dump_subtask(_make_subtask(), to=str(tmp_path / "single.yml"))
        assert (tmp_path / "tests" / "task" / "sub.yml").exists()
        assert (tmp_path / "single.yml").exists()

    def test_paths_are_portable(self, tmp_path):
        """Paths are written as pathlib.Path, which loads on every Python version and OS."""
        case = TestCase(inputs=((pathlib.PurePosixPath("a/b.txt"),), {}), expected=((), {}))
        dump_subtask(_make_subtask(cases=[case]), to=tmp_path / "paths.yml")
        text = (tmp_path / "paths.yml").read_text()
        assert "python/object/apply:pathlib.Path" in text
        assert "PosixPath" not in text
        with (tmp_path / "paths.yml").open("rb") as f:
            assert yaml.unsafe_load(f).cases[0].inputs[0][0] == pathlib.Path("a/b.txt")

    def test_lambda_is_refused(self, tmp_path):
        """Functions that students' kernels cannot import are refused at dump time."""
        subtask = _make_subtask(assertions={(lambda case, outputs: None): ((), {})})
        with pytest.raises(yaml.representer.RepresenterError, match="importable module"):
            dump_subtask(subtask, to=tmp_path / "lambda.yml")
        assert not (tmp_path / "lambda.yml").exists()

    def test_main_function_is_refused(self, tmp_path):
        """Functions defined in __main__ (e.g. an instructor's notebook) are refused."""

        def check(case, outputs):
            return None

        check.__module__ = "__main__"
        check.__qualname__ = "check"
        with pytest.raises(yaml.representer.RepresenterError, match="__main__.check"):
            dump_subtask(_make_subtask(assertions={check: ((), {})}), to=tmp_path / "main.yml")

    def test_library_functions_are_dumped(self, tmp_path):
        """Functions from importable modules are dumped by name."""
        dump_subtask(_make_subtask(assertions={equal_value: ((), {})}), to=tmp_path / "ok.yml")
        with (tmp_path / "ok.yml").open("rb") as f:
            assert equal_value in yaml.unsafe_load(f).assertions


class _Checks:
    """Holder for a static method that cannot be imported by module and name."""

    @staticmethod
    def positive(case, outputs):
        """Return nothing."""


class TestDumpReviewRegressions:
    """Regressions found while reviewing the fixes above."""

    def test_method_is_refused(self, tmp_path):
        """A static method would be written as <module>.<name>, which does not resolve."""
        with pytest.raises(yaml.representer.RepresenterError, match="top level of an importable module"):
            dump_subtask(_make_subtask(assertions={_Checks.positive: ((), {})}), to=tmp_path / "method.yml")

    def test_inline_wrapper_is_refused(self, tmp_path):
        """A wrapper created inline would load as the wrapped function, a different object."""
        wrapper = functools.wraps(equal_value)(lambda *a, **kw: None)
        with pytest.raises(yaml.representer.RepresenterError):
            dump_subtask(_make_subtask(assertions={wrapper: ((), {})}), to=tmp_path / "wrapper.yml")

    def test_append_list_of_pairs(self, tmp_path):
        """Appending merges assertions given as lists of pairs."""
        yaml_file = tmp_path / "pairs.yml"
        dump_subtask(_make_subtask(assertions=[(equal_value, (("a",), {}))]), to=yaml_file)
        dump_subtask(_make_subtask(assertions={equal_value: (("b",), {})}), to=yaml_file, append=True)
        with yaml_file.open("rb") as f:
            loaded = yaml.unsafe_load(f)
        assert loaded.assertions == [(equal_value, (("a",), {})), (equal_value, (("b",), {}))]
