"""Notebook-side entry point for running pytest with test cases."""

import pathlib

import pytest

from pytest_nbgrader import conftest, harness, loader


def main(*args, task=None, subtask=None, case_dir="tests", auto=True, **kwargs):
    """
    Wrap around pytest to inject test cases and set up config.

    Parameters
    ----------
    *args : str
        Additional arguments passed to ``pytest.main``.
    task : str or None, optional
        Task name subdirectory, by default None.
    subtask : str or None, optional
        Subtask name for the YAML file, by default None.
    case_dir : str, optional
        Directory containing test case files, by default ``"tests"``.
    auto : bool, optional
        Whether to auto-generate test class, by default True.
    **kwargs : dict
        Additional keyword arguments passed to ``pytest.main``.

    Returns
    -------
    int
        The pytest exit code.
    """
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
    """
    Context manager for a temporary symlink to a module file.

    Parameters
    ----------
    module : module
        The Python module to symlink.
    destination : str or None, optional
        Destination filename, by default uses the module's filename.
    """

    def __init__(self, module, destination=None):
        """
        Initialize the symlink manager.

        Parameters
        ----------
        module : module
            The Python module to symlink.
        destination : str or None, optional
            Destination filename, by default uses the module's filename.
        """
        self.module = module
        if destination is None:
            destination = pathlib.Path(module.__file__).name
        self.path = pathlib.Path(destination)
        self.custom = self.path.exists()

    def __enter__(self):
        """
        Create the symlink if no custom file exists.

        Returns
        -------
        pathlib.Path
            The symlink path.
        """
        if not self.custom:
            self.path.symlink_to(self.module.__file__)
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Remove the symlink if it was created by this manager.

        Parameters
        ----------
        exc_type : type or None
            Exception type, if any.
        exc_value : BaseException or None
            Exception value, if any.
        traceback : types.TracebackType or None
            Traceback, if any.
        """
        if not self.custom:
            self.path.unlink()


class TemporarySymlinks:
    """
    Context manager for multiple temporary symlinks.

    Parameters
    ----------
    *args : module
        Modules to create symlinks for.
    **kwargs : module
        Mapping of destination names to modules.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize with modules to symlink.

        Parameters
        ----------
        *args : module
            Modules to create symlinks for.
        **kwargs : module
            Mapping of destination names to modules.
        """
        self.symlinks = [TemporarySymlink(module) for module in args] + [TemporarySymlink(v, destination=k) for k, v in kwargs.items()]

    def __enter__(self):
        """
        Create all symlinks.

        Returns
        -------
        TemporarySymlinks
            The manager instance.
        """
        for symlink in self.symlinks:
            symlink.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Remove all symlinks.

        Parameters
        ----------
        exc_type : type or None
            Exception type, if any.
        exc_value : BaseException or None
            Exception value, if any.
        traceback : types.TracebackType or None
            Traceback, if any.
        """
        for symlink in self.symlinks:
            symlink.__exit__(exc_type, exc_value, traceback)
