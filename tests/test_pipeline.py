"""End-to-end tests: real pytest sessions through the plugin and ``runner.main``."""

import sys
import textwrap

import pytest

from pytest_nbgrader.assertions import equal_attributes, equal_contents, equal_value, raises
from pytest_nbgrader.cases import TestCase, TestSubtask
from pytest_nbgrader.dumper import dump_subtask
from pytest_nbgrader.loader import Submission
from pytest_nbgrader.prerequisites import has_signature


class Point:
    """Reference class for class submissions (must be importable to be dumped)."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


ADDITION = TestSubtask(
    cases=[
        TestCase(inputs=((2, 3), {}), expected=((5,), {})),
        TestCase(inputs=((0, 0), {}), expected=((0,), {})),
    ],
    assertions={equal_value: ((), {})},
)


@pytest.fixture(autouse=True)
def _restore_submission():
    """Save and restore Submission.submission around each test."""
    saved = Submission.submission
    yield
    Submission.submission = saved


def _run(pytester, subtask, submission, *args):
    """Dump ``subtask``, store ``submission`` and run pytest with ``--cases`` in-process."""
    dump_subtask(subtask, to=pytester.path / "cases.yml")
    Submission.submission = submission
    return pytester.runpytest_inprocess("-p", "no:cacheprovider", "--cases", "cases.yml", *args)


# ---------------------------------------------------------------------------
# pytest --cases
# ---------------------------------------------------------------------------


class TestCasesOption:
    """Grading runs through the auto-loaded plugin."""

    def test_correct_submission(self, pytester):
        """A correct function passes every case; the missing prerequisites are one skip."""
        result = _run(pytester, ADDITION, lambda a, b: a + b)
        result.assert_outcomes(passed=2, skipped=1)
        assert result.ret == pytest.ExitCode.OK

    def test_wrong_submission(self, pytester):
        """A wrong function fails with readable test ids."""
        result = _run(pytester, ADDITION, lambda a, b: a - b, "-v")
        result.assert_outcomes(passed=1, failed=1, skipped=1)
        result.stdout.fnmatch_lines(["*test_assertion?equal_value-0? FAILED*", "*failed with result TESTS_FAILED*"])

    def test_no_collection_warning(self, pytester):
        """The TestCase/TestSubtask dataclasses are not mistaken for test classes."""
        result = _run(pytester, ADDITION, lambda a, b: a + b, "-W", "error::pytest.PytestCollectionWarning")
        assert result.ret == pytest.ExitCode.OK

    def test_no_empty_parameter_set(self, pytester):
        """Subtasks without prerequisites work with empty_parameter_set_mark = fail_at_collect."""
        pytester.makeini("[pytest]\nempty_parameter_set_mark = fail_at_collect\n")
        result = _run(pytester, ADDITION, lambda a, b: a + b)
        assert result.ret == pytest.ExitCode.OK

    def test_stub_fails_equal_contents(self, pytester):
        """A function that returns nothing does not pass equal_contents."""
        subtask = TestSubtask(cases=[TestCase(inputs=((3,), {}), expected=(([0, 1, 2],), {}))], assertions={equal_contents: ((), {})})
        result = _run(pytester, subtask, lambda n: None)
        result.assert_outcomes(failed=1, skipped=1)

    def test_labelled_prerequisites(self, pytester):
        """The documented ``{"label": (function, (args, kwargs))}`` prerequisites form works."""
        import inspect

        subtask = TestSubtask(
            cases=ADDITION.cases,
            assertions=ADDITION.assertions,
            prerequisites={"signature": (has_signature, ((inspect.signature(lambda a, b: None),), {}))},
        )
        result = _run(pytester, subtask, lambda a, b: a + b)
        result.assert_outcomes(passed=3)

    def test_system_exit_affects_only_its_case(self, pytester):
        """A student calling sys.exit fails that case only."""

        def safe_sqrt(x):
            if x < 0:
                sys.exit("negative input")
            return x**0.5

        subtask = TestSubtask(
            cases=[TestCase(inputs=((-1,), {}), expected=((0.0,), {})), TestCase(inputs=((4,), {}), expected=((2.0,), {}))],
            assertions={equal_value: ((), {})},
        )
        result = _run(pytester, subtask, safe_sqrt)
        result.assert_outcomes(passed=1, errors=1, skipped=1)
        result.stdout.fnmatch_lines(["*SystemExit: negative input*"])


class TestRaisesCases:
    """Subtasks mixing raises=True cases with value assertions."""

    SUBTASK = TestSubtask(
        cases=[
            TestCase(inputs=((6, 3), {}), expected=((2.0,), {})),
            TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True),
        ],
        assertions={equal_value: ((), {}), raises: ((ZeroDivisionError,), {})},
    )

    def test_correct_submission(self, pytester):
        """A correct submission passes: value assertions do not run on the expected exception."""
        result = _run(pytester, self.SUBTASK, lambda a, b: a / b)
        result.assert_outcomes(passed=4, skipped=1)

    def test_non_raising_submission(self, pytester):
        """A submission that returns instead of raising fails."""
        result = _run(pytester, self.SUBTASK, lambda a, b: a / b if b else float("inf"))
        result.assert_outcomes(passed=2, failed=2, skipped=1)

    def test_plugin_errors_are_not_the_expected_exception(self, pytester):
        """A student who returns a number never satisfies raises(TypeError)."""
        subtask = TestSubtask(
            cases=[TestCase(inputs=(("a",), {}), expected=((), {}), raises=True)],
            assertions={raises: ((TypeError,), {})},
        )
        result = _run(pytester, subtask, lambda x: 0)
        result.assert_outcomes(failed=1, skipped=1)


class TestClassSubmissions:
    """Class submissions with several instantiations."""

    SUBTASK = TestSubtask(
        cases=[TestCase(inputs=[((1, 2), {}), ((3, 4), {})], expected=((Point(1, 2), Point(3, 4)), {}))],
        assertions={equal_attributes: (("x", "y"), {})},
    )

    def test_correct_class(self, pytester):
        """A correct class passes."""
        result = _run(pytester, self.SUBTASK, Point)
        result.assert_outcomes(passed=1, skipped=1)

    def test_second_instance_wrong(self, pytester):
        """A class that is only wrong for the second instance fails with a readable message."""

        class Wrong:
            def __init__(self, x, y):
                self.x, self.y = x, (y if x < 3 else -999)

        result = _run(pytester, self.SUBTASK, Wrong)
        result.assert_outcomes(failed=1, skipped=1)
        result.stdout.fnmatch_lines(["*Test case failed:*", "1, 2; 3, 4"])
        result.stdout.no_fnmatch_line("*IndexError*")


class TestUsageErrors:
    """Configuration mistakes are reported clearly."""

    def test_missing_cases_file(self, pytester):
        """A wrong --cases path is a usage error."""
        Submission.submission = lambda: None
        result = pytester.runpytest_inprocess("--cases", "typo.yml")
        assert result.ret == pytest.ExitCode.USAGE_ERROR
        result.stderr.fnmatch_lines(["*cannot load test cases from 'typo.yml'*"])

    def test_nothing_to_test(self, pytester):
        """A subtask without assertions does not pass silently."""
        result = _run(pytester, TestSubtask(cases=ADDITION.cases, assertions={}), lambda a, b: "wrong")
        assert result.ret != pytest.ExitCode.OK
        result.stdout.fnmatch_lines(["*nothing would be tested*"])

    def test_no_submission(self, pytester):
        """Running without a submission says so."""
        result = _run(pytester, ADDITION, None)
        result.stdout.fnmatch_lines(["*no submission found*"])
        assert result.ret != pytest.ExitCode.OK


def test_unrelated_project_is_unaffected(pytester):
    """The auto-loaded plugin emits no warnings in projects that do not use it."""
    pytester.makepyfile("def test_one():\n    pass\n\ndef test_two(tmp_path):\n    pass\n")
    result = pytester.runpytest_inprocess("-p", "no:cacheprovider", "-W", "error")
    result.assert_outcomes(passed=2)


# ---------------------------------------------------------------------------
# runner.main in a fresh interpreter (as in a notebook kernel)
# ---------------------------------------------------------------------------


NOTEBOOK = """
import os
import pathlib
import sys

from pytest_nbgrader import runner
from pytest_nbgrader.assertions import equal_value
from pytest_nbgrader.cases import TestCase, TestSubtask
from pytest_nbgrader.dumper import dump_subtask
from pytest_nbgrader.loader import Submission

for directory in ("first", "second"):
    dump_subtask(
        TestSubtask(cases=[TestCase(inputs=((2, 3), {{}}), expected=((5,), {{}}))], assertions={{equal_value: ((), {{}})}}),
        to=pathlib.Path(directory, "tests", "Addition", "basic.yml"),
    )

def add(a, b):
    return a + b

Submission.submit(add)
{body}
"""


def _notebook(pytester, body):
    """Run a notebook-like script in a fresh interpreter and return its stdout lines."""
    script = pytester.path / "notebook.py"
    script.write_text(NOTEBOOK.format(body=textwrap.dedent(body)))
    result = pytester.runpython(script)
    assert result.ret == 0, "\n".join(result.outlines + result.errlines)
    return result.outlines


class TestRunnerMain:
    """runner.main end to end."""

    def test_auto_and_cleanup(self, pytester):
        """auto=True grades the subtask and leaves no files behind."""
        lines = _notebook(
            pytester,
            """
            os.chdir("first")
            print("RC", int(runner.main("-q", task="Addition", subtask="basic")))
            print("FILES", sorted(p.name for p in pathlib.Path().glob("*.py")))
            """,
        )
        assert "RC 0" in lines
        assert "FILES []" in lines

    def test_auto_false_runs_no_generated_tests(self, pytester):
        """auto=False does not run the built-in test class."""
        lines = _notebook(
            pytester,
            """
            os.chdir("first")
            print("RC", int(runner.main("-q", task="Addition", subtask="basic", auto=False)))
            """,
        )
        assert f"RC {int(pytest.ExitCode.NO_TESTS_COLLECTED)}" in lines

    def test_rerun_after_chdir(self, pytester):
        """A second run from another directory in the same process works."""
        lines = _notebook(
            pytester,
            """
            os.chdir("first")
            print("RC1", int(runner.main("-q", task="Addition", subtask="basic")))
            os.chdir("../second")
            print("RC2", int(runner.main("-q", task="Addition", subtask="basic")))
            """,
        )
        assert "RC1 0" in lines
        assert "RC2 0" in lines

    def test_leftover_symlinks_are_cleaned(self, pytester):
        """Symlinks left behind by an interrupted run are replaced and removed."""
        lines = _notebook(
            pytester,
            """
            from pytest_nbgrader import conftest, harness
            os.chdir("first")
            pathlib.Path("conftest.py").symlink_to(conftest.__file__)
            pathlib.Path("harness.py").symlink_to(harness.__file__)
            print("RC", int(runner.main("-q", task="Addition", subtask="basic")))
            print("FILES", sorted(p.name for p in pathlib.Path().glob("*.py")))
            """,
        )
        assert "RC 0" in lines
        assert "FILES []" in lines
