"""Notebook-side entry point for running pytest with test cases."""

from __future__ import annotations


__all__ = ["TemporarySymlink", "TemporarySymlinks", "main"]

import contextlib
import pathlib
import sys
import types as _types

import pytest

from pytest_nbgrader import conftest, harness, loader


def main(
    *args: str,
    task: str | None = None,
    subtask: str | None = None,
    case_dir: str = "tests",
    auto: bool = True,
    **kwargs: object,
) -> pytest.ExitCode | int:
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
        Whether to run the built-in test class (``harness.py::TestClass``), by default True.
        With ``auto=False`` only the tests passed in ``*args`` are run.
    **kwargs : dict
        Additional keyword arguments passed to ``pytest.main``.

    Returns
    -------
    int
        The pytest exit code.

    Raises
    ------
    RuntimeError
        If no submission has been stored.
    ValueError
        If ``task`` is given without ``subtask``.
    FileNotFoundError
        If the test cases file does not exist.
    """
    # ensure existence of submission
    if loader.Submission.submission is None:
        raise RuntimeError("No submission found. Call submit() first.")
    if task is not None and subtask is None:
        raise ValueError("task requires subtask.")

    # The harness is added explicitly below, so the plugin must not generate its own test file.
    pytest_args = ["-p", "no:pytest-nbgrader", "--noauto", "-W", "ignore::pytest.PytestAssertRewriteWarning"]

    if subtask is not None:
        cases = pathlib.Path(case_dir) / (task or "") / f"{subtask}.yml"
        if not cases.is_file():
            raise FileNotFoundError("Test cases could not be found.")
        pytest_args.append(f"--{cases=!s}")

    pytest_args.extend(args)

    if auto:
        pytest_args.append("harness.py::TestClass")

    # pytest keeps the symlinked harness imported as module "harness"; a stale entry from a run in
    # another directory would make pytest refuse to import it again ("import file mismatch").
    stale = getattr(sys.modules.get("harness"), "__file__", None)
    if stale is not None:
        stale_path, harness_path = pathlib.Path(stale), pathlib.Path(harness.__file__)
        if stale_path.name == harness_path.name and (not stale_path.exists() or stale_path.resolve() == harness_path.resolve()):
            del sys.modules["harness"]

    with TemporarySymlinks(conftest, harness):
        return pytest.main(pytest_args, **kwargs)


def _links_to(path: pathlib.Path, module: _types.ModuleType) -> bool:
    """
    Tell whether ``path`` is a symlink to the file of ``module``.

    Parameters
    ----------
    path : pathlib.Path
        Path to check.
    module : module
        The module whose file the link should point to.

    Returns
    -------
    bool
        True if ``path`` is a symlink resolving to the module's file, or a dangling symlink to a
        file of the same name in a directory of the same name (e.g. left over from another environment).
    """
    if not path.is_symlink():
        return False
    target = pathlib.Path(module.__file__)
    if path.exists():
        return path.resolve() == target.resolve()
    link = path.readlink()
    return (link.name, link.parent.name) == (target.name, target.parent.name)


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

    module: _types.ModuleType
    path: pathlib.Path
    custom: bool

    def __init__(self, module: _types.ModuleType, destination: str | None = None) -> None:
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
        self.custom = False

    def __enter__(self) -> pathlib.Path:
        """
        Create the symlink if no custom file exists.

        A symlink to the module left behind by an interrupted run is replaced (and removed on exit).

        Returns
        -------
        pathlib.Path
            The symlink path.
        """
        if _links_to(self.path, self.module):
            self.path.unlink()
        self.custom = self.path.exists() or self.path.is_symlink()
        if not self.custom:
            self.path.symlink_to(self.module.__file__)
        return self.path

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _types.TracebackType | None,
    ) -> None:
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
            self.path.unlink(missing_ok=True)


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

    symlinks: list[TemporarySymlink]
    _stack: contextlib.ExitStack

    def __init__(self, *args: _types.ModuleType, **kwargs: _types.ModuleType) -> None:
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

    def __enter__(self) -> TemporarySymlinks:
        """
        Create all symlinks.

        Returns
        -------
        TemporarySymlinks
            The manager instance.
        """
        with contextlib.ExitStack() as stack:
            for symlink in self.symlinks:
                stack.enter_context(symlink)
            # keep the symlinks only if all of them were created
            self._stack = stack.pop_all()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _types.TracebackType | None,
    ) -> None:
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
        self._stack.__exit__(exc_type, exc_value, traceback)
