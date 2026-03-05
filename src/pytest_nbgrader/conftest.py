"""pytest configuration module

pytest internals:
  pytest_addoption -- add custom options to test a single subtask at a time
  pytest_generate_tests -- generate tests programmatically from `tests.pickle`

pytest fixtures:
  verbosity -- provide verbosity level for outputs
  submission -- provide student submission

PYTEST_DONT_REWRITE
"""

import pathlib
import pytest
import pytest_nbgrader
import warnings


def pytest_addoption(parser):
    """Add custom options"""
    parser.addoption(
        '--cases',
        action='store',
        dest='cases',
        default=None,
        help='specify location of test cases in yml format',
    )
    parser.addoption(
        '--noauto',
        action='store_false',
        dest='auto',
        default=True,
        help='Do not generate tests with pytest-nbgrader',
    )


def pytest_sessionstart(session):
    """Collect manual and automatic test cases."""
    import yaml

    # TODO: Collect yaml files with pytest_collection instead
    cases = session.config.getoption('cases')
    if cases is not None:
        # load cases from yaml
        assert pathlib.Path(cases).is_file(), f'{cases=} is not a file.'
        with open(cases, 'rb') as f:
            test_cases = yaml.unsafe_load(f)
        session.config.option.test_cases = test_cases

        if session.config.option.auto:
            import uuid

            test_file = pathlib.Path(f'test_auto_{uuid.uuid4()}.py')
            test_file.symlink_to(pytest_nbgrader.harness.__file__)
            session.config.option.auto = test_file

    else:
        session.config.option.test_cases = None


def pytest_sessionfinish(session):
    """At session finish, unlink the previously generated tests file."""
    if isinstance(session.config.option.auto, pathlib.Path):
        session.config.option.auto.unlink()


def pytest_generate_tests(metafunc):
    """Programmatically generate tests from deserialized test cases"""

    cases = metafunc.config.getoption('test_cases')
    if cases:
        for fixture in ['prerequisites', 'assertions', 'cases']:
            if fixture in metafunc.fixturenames:
                parameters = getattr(cases, fixture)
                if isinstance(parameters, dict):
                    parameters = parameters.items()
                metafunc.parametrize(fixture, parameters)

    else:
        warnings.warn(
            UserWarning('pytest-nbgrader: No data for automatic tests found.')
        )


@pytest.fixture
def verbosity(request):
    """Inject verbosity from global config."""
    return request.config.getoption('verbose')


@pytest.fixture
def submission():
    """Inject submission object into pytest as fixture."""
    return pytest_nbgrader.loader.Submission.submission
