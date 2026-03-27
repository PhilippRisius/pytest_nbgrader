"""Tests for loader.py — Submission.submit() dispatch paths and print output."""

import importlib.machinery
import types

from pytest_nbgrader.loader import Submission


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
        """submit(function) prints function source code."""

        def my_func():
            return 42

        Submission.submit(my_func)
        captured = capsys.readouterr()
        assert "will be tested" in captured.out
        assert "my_func" in captured.out

    def test_string_prints_code(self, capsys):
        """submit(str) prints the code string."""
        Submission.submit("x = 1 + 2")
        captured = capsys.readouterr()
        assert "will be tested" in captured.out
        assert "x = 1 + 2" in captured.out

    def test_class_prints_notice(self, capsys):
        """submit(type) prints class notice."""

        class MyClass:
            pass

        Submission.submit(MyClass)
        captured = capsys.readouterr()
        assert "will be tested" in captured.out

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
