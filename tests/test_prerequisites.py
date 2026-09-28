"""Tests for prerequisites.py — has_signature, writes, writes_file."""

import importlib.util
import inspect
import os
import pathlib
import sys

import pytest

from pytest_nbgrader.prerequisites import has_signature, writes, writes_file


def _make_spec(directory, name, code):
    """Write code to a file and return its ModuleSpec."""
    path = directory / f"{name}.py"
    path.write_text(code)
    return importlib.util.spec_from_file_location(name, path)


# ---------------------------------------------------------------------------
# has_signature
# ---------------------------------------------------------------------------


class TestHasSignatureNames:
    """Tests for parameter name comparison."""

    def test_matching_names(self):
        """Identical parameter names → OK."""

        def func(a, b):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref) == pytest.ExitCode.OK

    def test_different_names(self):
        """Different parameter names → TESTS_FAILED."""

        def func(x, y):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref) == pytest.ExitCode.TESTS_FAILED

    def test_extra_params(self):
        """More params than reference → TESTS_FAILED."""

        def func(a, b, c):
            return a, b, c

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref) == pytest.ExitCode.TESTS_FAILED

    def test_fewer_params(self):
        """Fewer params than reference → TESTS_FAILED."""

        def func(a):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref) == pytest.ExitCode.TESTS_FAILED

    def test_custom_compare_names_set_equality(self):
        """Custom compare_names with set equality ignores order."""

        def func(b, a):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref) == pytest.ExitCode.TESTS_FAILED
        assert has_signature(func, ref, compare_names=lambda a, b: set(a) == set(b)) == pytest.ExitCode.OK

    def test_no_comparisons_names_only(self):
        """Without attribute comparisons, only names are checked."""

        def func(a: int = 5):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter(
                    "a",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=99,
                    annotation=str,
                ),
            ]
        )
        assert has_signature(func, ref) == pytest.ExitCode.OK


class TestHasSignatureStrict:
    """Tests for strict_comparisons (positional args)."""

    def test_kind_match(self):
        """Strict kind: both POSITIONAL_OR_KEYWORD → OK."""

        def func(a, b):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref, "kind") == pytest.ExitCode.OK

    def test_kind_mismatch(self):
        """Strict kind: keyword-only vs positional → TESTS_FAILED."""

        def func(*, a):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ]
        )
        assert has_signature(func, ref, "kind") == pytest.ExitCode.TESTS_FAILED

    def test_default_match(self):
        """Strict default: same defaults → OK."""

        def func(a=10):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=10),
            ]
        )
        assert has_signature(func, ref, "default") == pytest.ExitCode.OK

    def test_default_mismatch(self):
        """Strict default: different defaults → TESTS_FAILED."""

        def func(a=10):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=20),
            ]
        )
        assert has_signature(func, ref, "default") == pytest.ExitCode.TESTS_FAILED

    def test_annotation_match(self):
        """Strict annotation on params and return → OK."""

        def func(a: int) -> str:
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter(
                    "a",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=int,
                ),
            ],
            return_annotation=str,
        )
        assert has_signature(func, ref, "annotation") == pytest.ExitCode.OK

    def test_annotation_param_mismatch(self):
        """Strict annotation: different param type → TESTS_FAILED."""

        def func(a: int):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter(
                    "a",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=str,
                ),
            ]
        )
        assert has_signature(func, ref, "annotation") == pytest.ExitCode.TESTS_FAILED

    def test_return_annotation_mismatch(self):
        """Return annotation differs → TESTS_FAILED."""

        def func(a) -> int:
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            ],
            return_annotation=str,
        )
        assert has_signature(func, ref, "annotation") == pytest.ExitCode.TESTS_FAILED


class TestHasSignatureCustomComparison:
    """Tests for comparison callables via **kwargs."""

    def test_custom_default_always_passes(self):
        """Custom comparison that always returns True overrides strict check."""

        def func(a=10):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=20),
            ]
        )
        assert has_signature(func, ref, "default") == pytest.ExitCode.TESTS_FAILED
        assert has_signature(func, ref, default=lambda a, b: True) == pytest.ExitCode.OK

    def test_strict_overrides_kwarg(self):
        """Strict comparison overrides kwarg for the same attribute."""

        def func(a=10):
            pass

        ref = inspect.Signature(
            parameters=[
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=20),
            ]
        )
        # "default" in strict_comparisons overwrites the kwarg lambda
        # because strict sets comparisons[attr] AFTER kwargs are populated
        assert has_signature(func, ref, "default", default=lambda a, b: True) == pytest.ExitCode.TESTS_FAILED


# ---------------------------------------------------------------------------
# writes
# ---------------------------------------------------------------------------


class TestWrites:
    """Tests for writes — stdout/stderr capture during module execution."""

    def test_stdout_match(self, tmp_path):
        """Module writes expected stdout → OK."""
        spec = _make_spec(tmp_path, "mod_out", "print('hello')")
        assert writes(spec, out="hello\n") == pytest.ExitCode.OK

    def test_stdout_mismatch(self, tmp_path):
        """Module writes wrong stdout → TESTS_FAILED."""
        spec = _make_spec(tmp_path, "mod_out2", "print('hello')")
        assert writes(spec, out="world\n") == pytest.ExitCode.TESTS_FAILED

    def test_stderr_match(self, tmp_path):
        """Module writes expected stderr → OK."""
        spec = _make_spec(
            tmp_path,
            "mod_err",
            "import sys; print('err', file=sys.stderr)",
        )
        assert writes(spec, err="err\n") == pytest.ExitCode.OK

    def test_stderr_mismatch(self, tmp_path):
        """Module writes wrong stderr → TESTS_FAILED."""
        spec = _make_spec(
            tmp_path,
            "mod_err2",
            "import sys; print('err', file=sys.stderr)",
        )
        assert writes(spec, err="different\n") == pytest.ExitCode.TESTS_FAILED

    def test_empty_stdout_expected(self, tmp_path):
        """Module writes nothing, expected empty string → OK."""
        spec = _make_spec(tmp_path, "mod_silent", "x = 1")
        assert writes(spec, out="") == pytest.ExitCode.OK

    def test_both_streams(self, tmp_path):
        """Both stdout and stderr checked simultaneously."""
        code = "import sys; print('out'); print('err', file=sys.stderr)"
        spec = _make_spec(tmp_path, "mod_both", code)
        assert writes(spec, out="out\n", err="err\n") == pytest.ExitCode.OK

    def test_name_override(self, tmp_path):
        """Name parameter overrides __name__ during execution and restores spec."""
        spec = _make_spec(tmp_path, "original", "print(__name__)")
        result = writes(spec, name="custom_name", out="custom_name\n")
        assert result == pytest.ExitCode.OK
        assert spec.name == "original"

    def test_unchecked_stream_ignored(self, tmp_path):
        """When only out is specified, err=None is not compared."""
        code = "import sys; print('hello'); print('noise', file=sys.stderr)"
        spec = _make_spec(tmp_path, "mod_partial", code)
        # Only check stdout — stderr should be ignored, not compared to None
        assert writes(spec, out="hello\n") == pytest.ExitCode.OK

    def test_no_expectations(self, tmp_path):
        """Neither out nor err specified → no comparisons, always OK."""
        spec = _make_spec(tmp_path, "mod_none", "print('anything')")
        assert writes(spec) == pytest.ExitCode.OK


# ---------------------------------------------------------------------------
# writes_file
# ---------------------------------------------------------------------------


class TestWritesFile:
    """Tests for writes_file — file system change detection."""

    def test_created_file_match(self, tmp_path, monkeypatch):
        """Module creates expected file → OK."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        spec = _make_spec(
            tmp_path,
            "creator",
            "import pathlib; pathlib.Path('output.txt').write_text('data')",
        )
        result = writes_file(spec, created={pathlib.Path("output.txt")})
        assert result == pytest.ExitCode.OK

    def test_created_file_mismatch(self, tmp_path, monkeypatch):
        """Module creates unexpected file → TESTS_FAILED."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        spec = _make_spec(
            tmp_path,
            "wrong_creator",
            "import pathlib; pathlib.Path('wrong.txt').write_text('data')",
        )
        result = writes_file(spec, created={pathlib.Path("expected.txt")})
        assert isinstance(result, tuple)
        assert result[0] == pytest.ExitCode.TESTS_FAILED

    def test_no_expectations(self, tmp_path, monkeypatch):
        """No created/deleted/modified expectations → OK."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        spec = _make_spec(tmp_path, "noop", "x = 1")
        assert writes_file(spec) == pytest.ExitCode.OK

    def test_modified_file_detected(self, tmp_path, monkeypatch):
        """Module modifies existing file → detected as modified."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        (workdir / "data.txt").write_text("old content")
        monkeypatch.chdir(workdir)

        spec = _make_spec(
            tmp_path,
            "modifier",
            "import pathlib; pathlib.Path('data.txt').write_text('new content is longer')",
        )
        result = writes_file(spec, modified={pathlib.Path("data.txt")})
        assert result == pytest.ExitCode.OK

    def test_deleted_file_detected(self, tmp_path, monkeypatch):
        """Module deletes file → detected as deleted."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        (workdir / "temp.txt").write_text("delete me")
        monkeypatch.chdir(workdir)

        spec = _make_spec(
            tmp_path,
            "deleter",
            "import pathlib; pathlib.Path('temp.txt').unlink()",
        )
        result = writes_file(spec, deleted={pathlib.Path("temp.txt")})
        assert result == pytest.ExitCode.OK

    def test_name_override_restores(self, tmp_path, monkeypatch):
        """Name override restores spec.name after execution."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        spec = _make_spec(tmp_path, "original_name", "x = 1")
        writes_file(spec, name="custom")
        assert spec.name == "original_name"

    def test_failure_includes_expected_and_actual(self, tmp_path, monkeypatch):
        """Failure tuple contains (TESTS_FAILED, expected_set, actual_set)."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        spec = _make_spec(
            tmp_path,
            "no_create",
            "x = 1",  # creates no files
        )
        result = writes_file(spec, created={pathlib.Path("missing.txt")})
        assert result[0] == pytest.ExitCode.TESTS_FAILED
        assert result[1] == {pathlib.Path("missing.txt")}
        assert result[2] == set()


# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------


class TestModuleExecutionRegressions:
    """Executing modules for writes/writes_file."""

    def test_module_in_cwd_bytecode_not_reported(self, tmp_path, monkeypatch):
        """The import system's __pycache__ is not reported as a file created by the student."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "dont_write_bytecode", False)
        spec = _make_spec(tmp_path, "student_in_cwd", "import pathlib; pathlib.Path('output.txt').write_text('data')")
        assert writes_file(spec, created={pathlib.Path("output.txt")}) == pytest.ExitCode.OK

    def test_reading_is_not_modifying(self, tmp_path, monkeypatch):
        """Reading a file (which may update its atime) does not count as modifying it."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        data = workdir / "data.csv"
        data.write_text("1,2,3\n")
        past = data.stat().st_mtime - 3600
        os.utime(data, (past - 3600, past))  # atime older than mtime: the next read updates it
        monkeypatch.chdir(workdir)
        spec = _make_spec(tmp_path, "reader", "import pathlib; pathlib.Path('data.csv').read_text()")
        assert writes_file(spec, modified=set()) == pytest.ExitCode.OK

    def test_same_size_rewrite_is_modification(self, tmp_path, monkeypatch):
        """Rewriting a file with content of the same size is detected."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        answer = workdir / "answer.txt"
        answer.write_text("00")
        os.utime(answer, ns=(0, 0))
        monkeypatch.chdir(workdir)
        spec = _make_spec(tmp_path, "rewriter", "import pathlib; pathlib.Path('answer.txt').write_text('42')")
        assert writes_file(spec, modified={pathlib.Path("answer.txt")}) == pytest.ExitCode.OK

    def test_string_paths_are_accepted(self, tmp_path, monkeypatch):
        """Expected paths may be given as strings."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        monkeypatch.chdir(workdir)
        spec = _make_spec(tmp_path, "str_creator", "import pathlib; pathlib.Path('out.txt').write_text('x')")
        assert writes_file(spec, created={"out.txt"}) == pytest.ExitCode.OK

    def test_dangling_symlink_in_cwd(self, tmp_path, monkeypatch):
        """Dangling symlinks in the working directory do not crash the file snapshot."""
        workdir = tmp_path / "work"
        workdir.mkdir()
        (workdir / "results.csv").symlink_to(tmp_path / "missing")
        monkeypatch.chdir(workdir)
        spec = _make_spec(tmp_path, "noop_link", "x = 1")
        assert writes_file(spec, created=set()) == pytest.ExitCode.OK

    @pytest.mark.parametrize("check", [writes, writes_file])
    def test_spec_untouched_when_module_raises(self, check, tmp_path, monkeypatch):
        """The shared spec is not renamed, even if the module raises."""
        monkeypatch.chdir(tmp_path)
        spec = _make_spec(tmp_path, "crashing", "if __name__ == '__main__':\n    raise RuntimeError('crash')")
        with pytest.raises(RuntimeError, match="crash"):
            check(spec, name="__main__")
        assert (spec.name, spec.loader.name) == ("crashing", "crashing")

    def test_sys_exit_zero_is_success(self, tmp_path, monkeypatch):
        """``sys.exit(main())`` with status 0 counts as a normal run."""
        monkeypatch.chdir(tmp_path)
        code = "import sys\n\ndef main():\n    print('Hello')\n    return 0\n\nif __name__ == '__main__':\n    sys.exit(main())\n"
        spec = _make_spec(tmp_path, "script", code)
        assert writes(spec, name="__main__", out="Hello\n") == pytest.ExitCode.OK
        assert writes_file(spec, name="__main__", created=set()) == pytest.ExitCode.OK

    def test_sys_exit_nonzero_fails(self, tmp_path, monkeypatch):
        """A non-zero exit status fails."""
        monkeypatch.chdir(tmp_path)
        spec = _make_spec(tmp_path, "failing_script", "import sys; print('Hello'); sys.exit(2)")
        assert writes(spec, out="Hello\n") == pytest.ExitCode.TESTS_FAILED
        assert writes_file(spec)[0] == pytest.ExitCode.TESTS_FAILED

    def test_argv_is_isolated(self, tmp_path, monkeypatch):
        """Scripts see their own command line, not the grading process's."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["ipykernel_launcher.py", "-f", "kernel.json"])
        code = (
            "import argparse\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('--name', default='World')\n"
            "print('Hello,', parser.parse_args().name)\n"
        )
        spec = _make_spec(tmp_path, "greet", code)
        assert writes(spec, name="__main__", out="Hello, World\n") == pytest.ExitCode.OK
        assert writes(spec, name="__main__", out="Hello, Ada\n", argv=["--name", "Ada"]) == pytest.ExitCode.OK
        assert sys.argv == ["ipykernel_launcher.py", "-f", "kernel.json"]

    def test_dataclass_script(self, tmp_path, monkeypatch):
        """Scripts using dataclasses with postponed annotations run."""
        monkeypatch.chdir(tmp_path)
        code = "from __future__ import annotations\nimport dataclasses\n\n@dataclasses.dataclass\nclass P:\n    x: int\n\nprint(P(1))\n"
        spec = _make_spec(tmp_path, "dc_script", code)
        assert writes(spec, out="P(x=1)\n") == pytest.ExitCode.OK
        assert writes(spec, name="__main__", out="P(x=1)\n") == pytest.ExitCode.OK


class TestHasSignatureRegressions:
    """Annotation handling in has_signature."""

    def test_postponed_annotations_are_evaluated(self, tmp_path):
        """String annotations from ``from __future__ import annotations`` compare as types."""
        spec = _make_spec(tmp_path, "annotated", "from __future__ import annotations\n\ndef area(r: float) -> float:\n    return r\n")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def reference(r: float) -> float:
            return r

        assert has_signature(module.area, inspect.signature(reference), "annotation") == pytest.ExitCode.OK

    def test_return_comparator_argument_order(self):
        """Custom comparators get (submission, reference) for the return annotation, too."""
        calls = []

        def compare(fun_value, ref_value):
            calls.append((fun_value, ref_value))
            return True

        def func(x: bool) -> bool:
            return x

        def ref(x: int) -> int:
            return x

        has_signature(func, inspect.signature(ref), annotation=compare)
        assert calls == [(bool, int), (bool, int)]
