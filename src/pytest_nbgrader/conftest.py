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

import pathlib
import warnings

import pytest

import pytest_nbgrader


def pytest_addoption(parser):
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


def pytest_sessionstart(session):
    """
    Collect manual and automatic test cases.

    Parameters
    ----------
    session : pytest.Session
        The pytest session object.
    """
    import yaml

    # TODO: Collect yaml files with pytest_collection instead
    cases = session.config.getoption("cases")
    if cases is not None:
        # load cases from yaml
        assert pathlib.Path(cases).is_file(), f"{cases=} is not a file."
        with pathlib.Path(cases).open("rb") as f:
            test_cases = yaml.unsafe_load(f)
        session.config.option.test_cases = test_cases

        if session.config.option.auto:
            import uuid

            test_file = pathlib.Path(f"test_auto_{uuid.uuid4()}.py")
            test_file.symlink_to(pytest_nbgrader.harness.__file__)
            session.config.option.auto = test_file

    else:
        session.config.option.test_cases = None


def pytest_sessionfinish(session):
    """
    Unlink the previously generated tests file at session finish.

    Parameters
    ----------
    session : pytest.Session
        The pytest session object.
    """
    if isinstance(session.config.option.auto, pathlib.Path):
        session.config.option.auto.unlink()


def pytest_generate_tests(metafunc):
    """
    Programmatically generate tests from deserialized test cases.

    Parameters
    ----------
    metafunc : pytest.Metafunc
        The metafunc object for parametrizing test functions.
    """
    cases = metafunc.config.getoption("test_cases")
    if cases:
        for fixture in ["prerequisites", "assertions", "cases"]:
            if fixture in metafunc.fixturenames:
                parameters = getattr(cases, fixture)
                if isinstance(parameters, dict):
                    parameters = parameters.items()
                metafunc.parametrize(fixture, parameters)

    else:
        warnings.warn(UserWarning("pytest-nbgrader: No data for automatic tests found."))


@pytest.fixture
def verbosity(request):
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
def submission():
    """
    Inject submission object into pytest as fixture.

    Returns
    -------
    object
        The stored student submission.
    """
    return pytest_nbgrader.loader.Submission.submission
