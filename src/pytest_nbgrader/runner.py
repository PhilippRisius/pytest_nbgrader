"""Notebook-side entry point for running pytest with test cases."""

import pathlib

import pytest

from pytest_nbgrader import conftest, harness, loader


def main(*args, task=None, subtask=None, case_dir="tests", auto=True, **kwargs):
    """Wrap around pytest to inject test cases and set up config"""
    # ensure existence of submission
    assert loader.Submission.submission

    pytest_args = ["-p", "no:pytest-nbgrader"]

    if subtask is not None:
        cases = pathlib.Path(case_dir) / (task or "") / f"{subtask}.yml"
        assert cases.is_file(), "Test cases could not be found."
        pytest_args.append(f"--{cases=!s}")

    pytest_args.extend(args)

    if auto:
        pytest_args.append("harness.py::TestClass")

    with TemporarySymlinks(conftest, harness):
        return pytest.main(pytest_args, **kwargs)


class TemporarySymlink:
    """Context manager for a temporary symlink to a module file."""

    def __init__(self, module, destination=None):
        self.module = module
        if destination is None:
            destination = pathlib.Path(module.__file__).name
        self.path = pathlib.Path(destination)
        self.custom = self.path.exists()

    def __enter__(self):  # noqa: D105
        if not self.custom:
            self.path.symlink_to(self.module.__file__)
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):  # noqa: D105
        if not self.custom:
            self.path.unlink()


class TemporarySymlinks:
    """Context manager for multiple temporary symlinks."""

    def __init__(self, *args, **kwargs):
        self.symlinks = [TemporarySymlink(module) for module in args] + [TemporarySymlink(v, destination=k) for k, v in kwargs.items()]

    def __enter__(self):  # noqa: D105
        for symlink in self.symlinks:
            symlink.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):  # noqa: D105
        for symlink in self.symlinks:
            symlink.__exit__(exc_type, exc_value, traceback)
