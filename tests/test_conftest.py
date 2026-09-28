"""Tests for conftest.py — pytest hooks and fixtures."""

import pathlib
import types
from unittest.mock import MagicMock

import pytest
import yaml

from pytest_nbgrader import conftest
from pytest_nbgrader.assertions import equal_value
from pytest_nbgrader.cases import TestCase, TestSubtask
from pytest_nbgrader.loader import Submission
from pytest_nbgrader.prerequisites import has_signature


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
        """Missing test_cases emits a UserWarning for tests using the plugin's fixtures."""
        metafunc = MagicMock()
        metafunc.config.getoption.return_value = None
        metafunc.fixturenames = ["cases"]

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


# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------


def _metafunc(test_cases, fixturenames):
    """Build a mock metafunc that records parametrize calls."""
    metafunc = MagicMock()
    metafunc.config.getoption.return_value = test_cases
    metafunc.fixturenames = fixturenames
    return metafunc


def _params(metafunc, fixture):
    """Return the pytest.param objects passed to parametrize for a fixture."""
    for call in metafunc.parametrize.call_args_list:
        if call.args[0] == fixture:
            return call.args[1]
    raise AssertionError(f"{fixture} was not parametrized")


class TestGenerateTestsRegressions:
    """Parametrization details."""

    def test_unrelated_tests_do_not_warn(self, recwarn):
        """Tests that use none of the plugin's fixtures are left alone (no warning)."""
        metafunc = _metafunc(None, ["tmp_path"])
        conftest.pytest_generate_tests(metafunc)
        assert not recwarn.list
        metafunc.parametrize.assert_not_called()

    def test_readable_ids(self):
        """Parameters get ids from assertion names and case indices."""
        subtask = TestSubtask(cases=[TestCase(), TestCase()], assertions={equal_value: ((), {})})
        metafunc = _metafunc(subtask, ["assertions", "cases"])
        conftest.pytest_generate_tests(metafunc)
        assert [p.id for p in _params(metafunc, "assertions")] == ["equal_value"]
        assert [p.id for p in _params(metafunc, "cases")] == ["0", "1"]

    def test_labelled_items_use_label_as_id(self):
        """Labelled prerequisites get the label as id."""
        subtask = TestSubtask(cases=[TestCase()], assertions={equal_value: ((), {})}, prerequisites={"signature": (has_signature, ((), {}))})
        metafunc = _metafunc(subtask, ["prerequisites"])
        conftest.pytest_generate_tests(metafunc)
        assert [p.id for p in _params(metafunc, "prerequisites")] == ["signature"]

    def test_no_prerequisites_is_one_skipped_parameter(self):
        """No prerequisites give one explicitly skipped parameter, not an empty parameter set."""
        subtask = TestSubtask(cases=[TestCase()], assertions={equal_value: ((), {})})
        metafunc = _metafunc(subtask, ["prerequisites"])
        conftest.pytest_generate_tests(metafunc)
        (param,) = _params(metafunc, "prerequisites")
        assert param.values == (None,)
        assert param.marks[0].name == "skip"

    @pytest.mark.parametrize(
        "subtask",
        [
            TestSubtask(cases=[TestCase()], assertions={}),
            TestSubtask(cases=[], assertions={equal_value: ((), {})}),
        ],
    )
    def test_nothing_to_test_fails(self, subtask):
        """A subtask without cases or assertions (and without prerequisites) cannot pass silently."""
        metafunc = _metafunc(subtask, ["assertions", "cases"])
        with pytest.raises(pytest.fail.Exception, match="nothing would be tested"):
            conftest.pytest_generate_tests(metafunc)

    def test_custom_harness_with_cases_only(self):
        """A custom harness that only uses cases may come without assertions."""
        subtask = TestSubtask(cases=[TestCase()], assertions={})
        metafunc = _metafunc(subtask, ["cases"])
        conftest.pytest_generate_tests(metafunc)
        assert len(_params(metafunc, "cases")) == 1


class TestSessionStartRegressions:
    """Loading errors are usage errors."""

    def test_missing_file(self, tmp_path):
        """A wrong --cases path is a usage error, not an internal error."""
        session = _make_session(cases_path=tmp_path / "typo.yml", auto=False)
        with pytest.raises(pytest.UsageError, match="cannot load test cases"):
            conftest.pytest_sessionstart(session)

    def test_invalid_yaml(self, tmp_path):
        """Broken YAML is a usage error."""
        yml = tmp_path / "broken.yml"
        yml.write_text("cases: [")
        session = _make_session(cases_path=yml, auto=False)
        with pytest.raises(pytest.UsageError, match="cannot load test cases"):
            conftest.pytest_sessionstart(session)

    def test_not_a_subtask(self, tmp_path, monkeypatch):
        """A file that does not hold a TestSubtask is a usage error, and no test file is created."""
        yml = tmp_path / "plain.yml"
        yml.write_text("key: value\n")
        monkeypatch.chdir(tmp_path)
        session = _make_session(cases_path=yml, auto=True)
        with pytest.raises(pytest.UsageError, match="does not contain a TestSubtask"):
            conftest.pytest_sessionstart(session)
        assert not list(tmp_path.glob("test_auto_*.py"))

    def test_sessionfinish_tolerates_missing_file(self, tmp_path):
        """Cleanup does not fail if the generated file is already gone."""
        option = types.SimpleNamespace(auto=tmp_path / "test_auto_gone.py")
        conftest.pytest_sessionfinish(types.SimpleNamespace(config=types.SimpleNamespace(option=option)))


class TestSubmissionFixture:
    """The submission fixture fails clearly without a submission."""

    def test_no_submission(self, monkeypatch):
        """A missing submission fails with an explanation instead of NotImplementedError later."""
        monkeypatch.setattr(Submission, "submission", None)
        with pytest.raises(pytest.fail.Exception, match="no submission found"):
            conftest.submission.__wrapped__()
