"""
Pytest configuration module.

pytest internals:
  pytest_addoption -- add custom options to test a single subtask at a time
  pytest_generate_tests -- generate tests programmatically from `tests.pickle`

pytest fixtures:
  verbosity -- provide verbosity level for outputs
  submission -- provide student submission

PYTEST_DONT_REWRITE
"""

from __future__ import annotations


__all__ = [
    "pytest_addoption",
    "pytest_generate_tests",
    "pytest_sessionfinish",
    "pytest_sessionstart",
    "submission",
    "verbosity",
]

import pathlib
import warnings

import pytest

import pytest_nbgrader


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Add custom options for test case location and auto-generation.

    Parameters
    ----------
    parser : _pytest.config.argparsing.Parser
        The pytest argument parser.
    """
    parser.addoption(
        "--cases",
        action="store",
        dest="cases",
        default=None,
        help="specify location of test cases in yml format",
    )
    parser.addoption(
        "--noauto",
        action="store_false",
        dest="auto",
        default=True,
        help="Do not generate tests with pytest-nbgrader",
    )


_FIXTURES = ("prerequisites", "assertions", "cases")


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Collect manual and automatic test cases.

    Parameters
    ----------
    session : pytest.Session
        The pytest session object.

    Raises
    ------
    pytest.UsageError
        If the test cases file cannot be loaded or does not contain a ``TestSubtask``.
    """
    import yaml

    # TODO: Collect yaml files with pytest_collection instead
    cases = session.config.getoption("cases")
    if cases is None:
        session.config.option.test_cases = None
        return

    # load cases from yaml
    try:
        with pathlib.Path(cases).open("rb") as f:
            test_cases = yaml.unsafe_load(f)
    except (OSError, yaml.YAMLError) as e:
        raise pytest.UsageError(f"pytest-nbgrader: cannot load test cases from {cases!r}: {e}") from e
    if not all(hasattr(test_cases, attribute) for attribute in ("cases", "assertions")):
        raise pytest.UsageError(f"pytest-nbgrader: {cases!r} does not contain a TestSubtask.")
    session.config.option.test_cases = test_cases

    if session.config.option.auto:
        import uuid

        test_file = pathlib.Path(f"test_auto_{uuid.uuid4()}.py")
        test_file.symlink_to(pytest_nbgrader.harness.__file__)
        session.config.option.auto = test_file


def pytest_sessionfinish(session: pytest.Session) -> None:
    """
    Unlink the previously generated tests file at session finish.

    Parameters
    ----------
    session : pytest.Session
        The pytest session object.
    """
    auto = getattr(session.config.option, "auto", None)
    if isinstance(auto, pathlib.Path):
        auto.unlink(missing_ok=True)


def _parameter(key: object, value: object) -> object:
    """
    Wrap a prerequisites or assertions dict item as a pytest parameter with a readable id.

    Parameters
    ----------
    key : object
        Function (or label) the item is keyed by.
    value : object
        The ``(args, kwargs)`` pair, or ``(function, (args, kwargs))`` for labelled items.

    Returns
    -------
    object
        A ``pytest.param`` of the ``(key, value)`` item.
    """
    return pytest.param((key, value), id=getattr(key, "__name__", str(key)))


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """
    Programmatically generate tests from deserialized test cases.

    Parameters
    ----------
    metafunc : pytest.Metafunc
        The metafunc object for parametrizing test functions.
    """
    requested = [fixture for fixture in _FIXTURES if fixture in metafunc.fixturenames]
    if not requested:
        return

    cases = metafunc.config.getoption("test_cases")
    if not cases:
        warnings.warn(UserWarning("pytest-nbgrader: No data for automatic tests found."), stacklevel=1)
        return

    prerequisites = getattr(cases, "prerequisites", None) or {}
    if {"cases", "assertions"} <= set(requested) and not (cases.cases and cases.assertions) and not prerequisites:
        pytest.fail(
            "pytest-nbgrader: the test cases define no cases or no assertions, so nothing would be tested. "
            "Pass --noauto if only a custom harness should run.",
            pytrace=False,
        )

    for fixture in requested:
        if fixture == "cases":
            parameters = [pytest.param(case, id=str(index)) for index, case in enumerate(cases.cases)]
        else:
            parameters = [_parameter(key, value) for key, value in (prerequisites if fixture == "prerequisites" else cases.assertions).items()]
        if fixture == "prerequisites" and not parameters:
            parameters = [pytest.param(None, id="none", marks=pytest.mark.skip(reason="no prerequisites"))]
        metafunc.parametrize(fixture, parameters)


@pytest.fixture
def verbosity(request: pytest.FixtureRequest) -> int:
    """
    Inject verbosity from global config.

    Parameters
    ----------
    request : pytest.FixtureRequest
        The pytest fixture request object.

    Returns
    -------
    int
        The verbosity level.
    """
    return request.config.getoption("verbose")


@pytest.fixture
def submission() -> object:
    """
    Inject submission object into pytest as fixture.

    Returns
    -------
    object
        The stored student submission.
    """
    stored = pytest_nbgrader.loader.Submission.submission
    if stored is None:
        pytest.fail("pytest-nbgrader: no submission found. Call Submission.submit() before running the tests.", pytrace=False)
    return stored
