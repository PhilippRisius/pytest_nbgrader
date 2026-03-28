"""Tests for runner.py — TemporarySymlink, TemporarySymlinks, main."""

import pathlib
import types

import pytest

from pytest_nbgrader.runner import TemporarySymlink, TemporarySymlinks, main


@pytest.fixture()
def fake_module(tmp_path):
    """Create a fake module with a real __file__ path."""
    src = tmp_path / "source" / "mymod.py"
    src.parent.mkdir()
    src.write_text("# fake module")
    return types.SimpleNamespace(__file__=str(src))


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    """Create and chdir into a working directory for symlink tests."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return work


# ---------------------------------------------------------------------------
# TemporarySymlink
# ---------------------------------------------------------------------------


class TestTemporarySymlink:
    """Tests for TemporarySymlink context manager."""

    def test_creates_and_removes(self, fake_module, workdir):
        """Symlink created on enter, removed on exit."""
        link = workdir / "mymod.py"
        with TemporarySymlink(fake_module):
            assert link.is_symlink()
        assert not link.exists()

    def test_custom_destination(self, fake_module, workdir):
        """Destination parameter overrides the module filename."""
        with TemporarySymlink(fake_module, destination="custom.py"):
            assert (workdir / "custom.py").is_symlink()
        assert not (workdir / "custom.py").exists()

    def test_existing_file_preserved(self, fake_module, workdir):
        """Pre-existing file is not overwritten or removed."""
        existing = workdir / "mymod.py"
        existing.write_text("original content")
        with TemporarySymlink(fake_module):
            assert existing.read_text() == "original content"
            assert not existing.is_symlink()
        assert existing.read_text() == "original content"

    def test_enter_returns_path(self, fake_module, workdir):
        """__enter__ returns a pathlib.Path with the expected name."""
        with TemporarySymlink(fake_module) as p:
            assert isinstance(p, pathlib.Path)
            assert p.name == "mymod.py"


# ---------------------------------------------------------------------------
# TemporarySymlinks
# ---------------------------------------------------------------------------


class TestTemporarySymlinks:
    """Tests for TemporarySymlinks batch context manager."""

    def test_batch_creates_and_removes(self, tmp_path, monkeypatch):
        """Multiple symlinks created and cleaned up together."""
        src1 = tmp_path / "source" / "mod_a.py"
        src2 = tmp_path / "source" / "mod_b.py"
        src1.parent.mkdir(exist_ok=True)
        src1.write_text("# a")
        src2.write_text("# b")
        mod1 = types.SimpleNamespace(__file__=str(src1))
        mod2 = types.SimpleNamespace(__file__=str(src2))

        work = tmp_path / "work"
        work.mkdir()
        monkeypatch.chdir(work)

        with TemporarySymlinks(mod1, mod2):
            assert (work / "mod_a.py").is_symlink()
            assert (work / "mod_b.py").is_symlink()
        assert not (work / "mod_a.py").exists()
        assert not (work / "mod_b.py").exists()


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() entry point."""

    def test_with_subtask_builds_cases_arg(self, tmp_path, monkeypatch):
        """Subtask argument produces --cases=<path> in pytest args."""
        # Create YAML file at case_dir/task/subtask.yml
        case_dir = tmp_path / "tests"
        task_dir = case_dir / "hw1"
        task_dir.mkdir(parents=True)
        yml = task_dir / "ex1.yml"
        yml.write_text("dummy: true")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pytest_nbgrader.loader.Submission.submission", "fake_submission")

        captured_args = []

        def mock_pytest_main(args, **kwargs):
            captured_args.extend(args)
            return pytest.ExitCode.OK

        monkeypatch.setattr("pytest.main", mock_pytest_main)

        main(task="hw1", subtask="ex1", case_dir=str(case_dir))

        assert "-p" in captured_args
        assert "no:pytest-nbgrader" in captured_args
        assert any("--cases=" in a for a in captured_args)
        assert "harness.py::TestClass" in captured_args

    def test_without_subtask_no_cases(self, tmp_path, monkeypatch):
        """No subtask means no --cases arg, but harness.py::TestClass still present."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pytest_nbgrader.loader.Submission.submission", "fake_submission")

        captured_args = []

        def mock_pytest_main(args, **kwargs):
            captured_args.extend(args)
            return pytest.ExitCode.OK

        monkeypatch.setattr("pytest.main", mock_pytest_main)

        main()

        assert not any("--cases" in a for a in captured_args)
        assert "harness.py::TestClass" in captured_args
