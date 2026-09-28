"""Tests for loader.py — Submission.submit() dispatch paths and print output."""

import __future__
import functools
import importlib.machinery
import sys
import types

import pytest

from pytest_nbgrader.loader import Submission


@pytest.fixture(autouse=True)
def _restore_submission():
    """Save and restore Submission.submission around each test."""
    saved = Submission.submission
    yield
    Submission.submission = saved


class TestSubmitPath:
    """Tests for submit(pathlib.Path) — file-based module submission."""

    def test_submit_path_stores_modulespec(self, tmp_path):
        """Submitting a Path stores a ModuleSpec."""
        mod_file = tmp_path / "student.py"
        mod_file.write_text("answer = 42\n")
        Submission.submit(mod_file)
        assert isinstance(Submission.submission, importlib.machinery.ModuleSpec)

    def test_submit_path_spec_has_correct_name(self, tmp_path):
        """ModuleSpec name matches the file stem."""
        mod_file = tmp_path / "my_solution.py"
        mod_file.write_text("x = 1\n")
        Submission.submit(mod_file)
        assert Submission.submission.name == "my_solution"

    def test_submit_path_returns_spec(self, tmp_path):
        """submit(Path) returns the ModuleSpec."""
        mod_file = tmp_path / "sol.py"
        mod_file.write_text("")
        result = Submission.submit(mod_file)
        assert isinstance(result, importlib.machinery.ModuleSpec)


class TestSubmitPrintOutput:
    """Tests that submit() prints informative messages."""

    def test_function_prints_source(self, capsys):
        """submit(function) prints actual source code of the function."""

        def my_func():
            return 42

        Submission.submit(my_func)
        captured = capsys.readouterr()
        assert "submission will be tested" in captured.out
        assert "def my_func" in captured.out
        assert "return 42" in captured.out

    def test_string_prints_code(self, capsys):
        """submit(str) prints the code string."""
        Submission.submit("x = 1 + 2")
        captured = capsys.readouterr()
        assert "will be tested" in captured.out
        assert "x = 1 + 2" in captured.out

    def test_class_prints_notice(self, capsys):
        """submit(type) prints class name and source-not-shown notice."""

        class MyClass:
            pass

        Submission.submit(MyClass)
        captured = capsys.readouterr()
        assert "MyClass" in captured.out
        assert "will be tested" in captured.out
        assert "source code not shown" in captured.out

    def test_path_prints_file_contents(self, tmp_path, capsys):
        """submit(Path) prints the file contents."""
        mod_file = tmp_path / "code.py"
        mod_file.write_text("result = 99\n")
        Submission.submit(mod_file)
        captured = capsys.readouterr()
        assert "will be tested" in captured.out
        assert "result = 99" in captured.out

    def test_generic_submit_prints(self, capsys):
        """submit(object) with generic type prints the object."""
        Submission.submit(12345)
        captured = capsys.readouterr()
        assert "12345" in captured.out


class TestSubmitGeneric:
    """Tests for the base singledispatch (generic object)."""

    def test_stores_generic_object(self):
        """Generic objects stored directly."""
        obj = {"key": "value"}
        Submission.submit(obj)
        assert Submission.submission == {"key": "value"}

    def test_submit_string_returns_code(self):
        """submit(str) returns compiled CodeType."""
        result = Submission.submit("y = 2")
        assert isinstance(result, types.CodeType)


class TestSubmitRegressions:
    """Failed submissions, callables and paths."""

    def test_failed_submit_clears_previous(self):
        """A submission that fails to compile does not leave the previous one in place."""
        Submission.submit("result = 1")
        with pytest.raises(SyntaxError):
            Submission.submit("result = +* 1")
        assert Submission.submission is None

    def test_code_does_not_inherit_future_flags(self):
        """Student code is compiled with its own __future__ flags, not the loader's."""
        code = Submission.submit("x: int = 5")
        assert not code.co_flags & __future__.annotations.compiler_flag

    def test_callable_without_source(self, capsys):
        """Callables without retrievable source are stored and shown by repr."""
        submission = functools.partial(pow, 2)
        assert Submission.submit(submission) is submission
        assert "functools.partial" in capsys.readouterr().out

    def test_generic_submission_is_returned(self):
        """The generic branch returns the stored submission like the others."""
        assert Submission.submit(42) == 42

    def test_non_python_path_raises(self, tmp_path):
        """A path that cannot be imported raises instead of storing None silently."""
        path = tmp_path / "notes.txt"
        path.write_text("x = 1\n")
        with pytest.raises(ValueError, match="cannot be imported"):
            Submission.submit(path)
        assert Submission.submission is None

    def test_path_read_as_utf8(self, pytester):
        """Module source is read as UTF-8 (the encoding of Python source files), whatever the locale."""
        (pytester.path / "sol.py").write_text("# Grüße\nx = 1\n", encoding="utf-8")
        script = pytester.makepyfile(
            check=(
                "import pathlib, warnings\n"
                "from pytest_nbgrader.loader import Submission\n"
                "warnings.simplefilter('error', EncodingWarning)\n"
                "Submission.submit(pathlib.Path('sol.py'))\n"
            )
        )
        # -X warn_default_encoding warns whenever a file is opened without an explicit encoding
        result = pytester.run(sys.executable, "-X", "warn_default_encoding", script)
        assert result.ret == 0, result.stderr.str()
