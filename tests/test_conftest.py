"""Tests for conftest.py — pytest hooks and fixtures."""

import pathlib
import types
from unittest.mock import MagicMock

import pytest
import yaml

from pytest_nbgrader import conftest
from pytest_nbgrader.cases import TestCase, TestSubtask
from pytest_nbgrader.loader import Submission


def _make_session(cases_path=None, auto=True):
    """Build a mock pytest session with SimpleNamespace."""
    option = types.SimpleNamespace(auto=auto)
    mapping = {"cases": str(cases_path) if cases_path else None, "auto": auto}
    config = types.SimpleNamespace(option=option, getoption=lambda key: mapping.get(key))
    return types.SimpleNamespace(config=config)


# ---------------------------------------------------------------------------
# pytest_addoption
# ---------------------------------------------------------------------------


class TestAddOption:
    """Tests for pytest_addoption hook."""

    def test_registers_cases_and_noauto(self):
        """Both --cases and --noauto options are registered."""
        parser = MagicMock()
        conftest.pytest_addoption(parser)
        assert parser.addoption.call_count == 2
        registered = [call.args[0] for call in parser.addoption.call_args_list]
        assert "--cases" in registered
        assert "--noauto" in registered


# ---------------------------------------------------------------------------
# pytest_sessionstart
# ---------------------------------------------------------------------------


class TestSessionStart:
    """Tests for pytest_sessionstart hook."""

    def test_no_cases_sets_none(self):
        """No --cases option sets test_cases to None."""
        session = _make_session(cases_path=None)
        conftest.pytest_sessionstart(session)
        assert session.config.option.test_cases is None

    def test_loads_yaml(self, tmp_path):
        """Valid YAML file is loaded and stored in session config."""
        subtask = TestSubtask(
            cases=[TestCase(inputs=((), {}), expected=((), {}))],
            assertions={"eq": ("equal_value", ((), {}))},
        )
        yml = tmp_path / "test.yml"
        with yml.open("w") as f:
            yaml.dump(subtask, f)

        session = _make_session(cases_path=yml, auto=False)
        conftest.pytest_sessionstart(session)
        assert isinstance(session.config.option.test_cases, TestSubtask)

    def test_auto_creates_symlink(self, tmp_path, monkeypatch):
        """With auto=True, a symlink test_auto_*.py is created."""
        subtask = TestSubtask(
            cases=[TestCase(inputs=((), {}), expected=((), {}))],
            assertions={},
        )
        yml = tmp_path / "test.yml"
        with yml.open("w") as f:
            yaml.dump(subtask, f)

        monkeypatch.chdir(tmp_path)
        session = _make_session(cases_path=yml, auto=True)
        conftest.pytest_sessionstart(session)

        try:
            auto_path = session.config.option.auto
            assert isinstance(auto_path, pathlib.Path)
            assert auto_path.is_symlink()
            assert auto_path.name.startswith("test_auto_")
        finally:
            conftest.pytest_sessionfinish(session)


# ---------------------------------------------------------------------------
# pytest_sessionfinish
# ---------------------------------------------------------------------------


class TestSessionFinish:
    """Tests for pytest_sessionfinish hook."""

    def test_unlinks_auto_path(self, tmp_path):
        """Auto-generated path is deleted by sessionfinish."""
        dummy = tmp_path / "test_auto_dummy.py"
        dummy.write_text("# dummy")
        option = types.SimpleNamespace(auto=dummy)
        config = types.SimpleNamespace(option=option)
        session = types.SimpleNamespace(config=config)

        conftest.pytest_sessionfinish(session)
        assert not dummy.exists()


# ---------------------------------------------------------------------------
# pytest_generate_tests
# ---------------------------------------------------------------------------


class TestGenerateTests:
    """Tests for pytest_generate_tests hook."""

    def test_parametrizes_fixtures(self):
        """Fixtures in fixturenames are parametrized from test_cases."""
        cases_list = [TestCase(inputs=((), {}), expected=((), {}))]
        test_cases = types.SimpleNamespace(
            cases=cases_list,
            assertions={"eq": ("equal_value", ((), {}))},
            prerequisites={"sig": ("has_signature", ((), {}))},
        )

        metafunc = MagicMock()
        metafunc.config.getoption.return_value = test_cases
        metafunc.fixturenames = ["cases", "assertions", "prerequisites"]

        conftest.pytest_generate_tests(metafunc)
        assert metafunc.parametrize.call_count == 3

    def test_no_cases_warns(self):
        """Missing test_cases emits a UserWarning."""
        metafunc = MagicMock()
        metafunc.config.getoption.return_value = None

        with pytest.warns(UserWarning, match="No data"):
            conftest.pytest_generate_tests(metafunc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class TestFixtures:
    """Tests for conftest fixtures."""

    def test_submission_returns_stored_value(self, monkeypatch):
        """Submission fixture returns whatever is in Submission.submission."""
        monkeypatch.setattr(Submission, "submission", "test_value")
        result = conftest.submission.__wrapped__()
        assert result == "test_value"
