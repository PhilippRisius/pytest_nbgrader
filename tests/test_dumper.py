"""Tests for dumper.py — dump_exercise, dump_task, dump_subtask append mode."""

import yaml

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
