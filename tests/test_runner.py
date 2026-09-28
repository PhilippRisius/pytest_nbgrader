"""Tests for runner.py — TemporarySymlink, TemporarySymlinks, main."""

import pathlib
import sys
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
        assert "--noauto" in captured_args
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


class TestMainRegressions:
    """Argument handling of main()."""

    @pytest.fixture()
    def captured_args(self, tmp_path, monkeypatch):
        """Chdir into tmp_path, store a submission and capture the arguments passed to pytest.main."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pytest_nbgrader.loader.Submission.submission", "fake_submission")
        captured = []

        def mock_pytest_main(args, **kwargs):
            captured.extend(args)
            return pytest.ExitCode.OK

        monkeypatch.setattr("pytest.main", mock_pytest_main)
        return captured

    def test_auto_false_disables_generated_tests(self, captured_args, tmp_path):
        """auto=False runs only the given tests: the plugin must not generate its own test file."""
        (tmp_path / "tests" / "hw1").mkdir(parents=True)
        (tmp_path / "tests" / "hw1" / "ex1.yml").write_text("dummy: true")
        main("tests/custom.py", task="hw1", subtask="ex1", auto=False)
        assert "--noauto" in captured_args
        assert "harness.py::TestClass" not in captured_args

    def test_no_noauto_without_cases(self, captured_args):
        """--noauto (defined by the symlinked conftest) is only passed together with --cases."""
        main("/elsewhere/test_other.py", auto=False)
        assert "--noauto" not in captured_args

    def test_falsy_submission_is_accepted(self, captured_args, monkeypatch):
        """Only a missing submission is rejected, not a falsy one."""
        monkeypatch.setattr("pytest_nbgrader.loader.Submission.submission", 0)
        assert main() is pytest.ExitCode.OK

    def test_missing_submission(self, captured_args, monkeypatch):
        """No submission raises RuntimeError."""
        monkeypatch.setattr("pytest_nbgrader.loader.Submission.submission", None)
        with pytest.raises(RuntimeError, match="No submission"):
            main()

    def test_task_without_subtask(self, captured_args):
        """A task without subtask is rejected instead of being ignored."""
        with pytest.raises(ValueError, match="subtask"):
            main(task="hw1")

    def test_stale_harness_module_is_dropped(self, captured_args, monkeypatch):
        """A harness module imported by an earlier run in another directory is removed from sys.modules."""
        stale = types.ModuleType("harness")
        stale.__file__ = "/nonexistent/previous/run/harness.py"
        monkeypatch.setitem(sys.modules, "harness", stale)
        main()
        assert "harness" not in sys.modules

    def test_foreign_harness_module_is_kept(self, captured_args, monkeypatch, tmp_path):
        """A user's own module named harness is left alone."""
        own = tmp_path / "elsewhere" / "harness.py"
        own.parent.mkdir()
        own.write_text("# mine")
        module = types.ModuleType("harness")
        module.__file__ = str(own)
        monkeypatch.setitem(sys.modules, "harness", module)
        main()
        assert sys.modules["harness"] is module


class TestSymlinkRegressions:
    """Symlinks are cleaned up reliably."""

    def test_partial_enter_cleans_up(self, tmp_path, monkeypatch):
        """If creating a later symlink fails, the earlier ones are removed."""
        src = tmp_path / "source"
        src.mkdir()
        (src / "mod_a.py").write_text("# a")
        (src / "mod_b.py").write_text("# b")
        mod_a = types.SimpleNamespace(__file__=str(src / "mod_a.py"))
        mod_b = types.SimpleNamespace(__file__=str(src / "mod_b.py"))
        work = tmp_path / "work"
        work.mkdir()
        monkeypatch.chdir(work)

        symlink_to = pathlib.Path.symlink_to

        def fail_for_mod_b(self, target):
            if self.name == "mod_b.py":
                raise OSError("A required privilege is not held by the client")
            symlink_to(self, target)

        monkeypatch.setattr(pathlib.Path, "symlink_to", fail_for_mod_b)
        with pytest.raises(OSError, match="privilege"), TemporarySymlinks(mod_a, mod_b):
            pass
        assert not (work / "mod_a.py").is_symlink()

    def test_valid_link_to_module_is_kept(self, fake_module, workdir):
        """A valid link to the module (e.g. created by the user) is used and left in place."""
        link = workdir / "mymod.py"
        link.symlink_to(fake_module.__file__)
        with TemporarySymlink(fake_module):
            assert link.is_symlink()
        assert link.is_symlink()

    def test_dangling_leftover_from_other_environment(self, fake_module, workdir, tmp_path):
        """A dangling symlink to the same module in another (removed) environment is replaced."""
        link = workdir / "mymod.py"
        link.symlink_to(tmp_path / "old_env" / "source" / "mymod.py")
        with TemporarySymlink(fake_module):
            assert link.resolve() == pathlib.Path(fake_module.__file__).resolve()
        assert not link.is_symlink()

    def test_exit_tolerates_removed_symlink(self, fake_module, workdir):
        """Cleanup does not raise if the symlink was already removed."""
        with TemporarySymlink(fake_module) as link:
            link.unlink()
