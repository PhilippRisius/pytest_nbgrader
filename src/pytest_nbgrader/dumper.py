"""Serialize test cases to YAML files."""

from __future__ import annotations


__all__ = ["dump_exercise", "dump_subtask", "dump_task"]

import os
import pathlib
import types

import yaml

from pytest_nbgrader.cases import TestSubtask


class _Dumper(yaml.Dumper):
    """YAML dumper for test cases that students' kernels can load."""


def _represent_function(dumper: yaml.Dumper, function: types.FunctionType) -> yaml.Node:
    """
    Represent a function by its import path, refusing functions that cannot be imported.

    Parameters
    ----------
    dumper : yaml.Dumper
        The active dumper.
    function : types.FunctionType
        Function to represent, e.g. an assertion.

    Returns
    -------
    yaml.Node
        A ``!!python/name`` node.

    Raises
    ------
    yaml.representer.RepresenterError
        If the function is defined in ``__main__`` or is a lambda or local function. Such
        references would resolve to the student's namespace, or not at all, when loaded.
    """
    if function.__module__ == "__main__" or "<" in function.__qualname__:
        raise yaml.representer.RepresenterError(
            f"cannot dump {function.__module__}.{function.__qualname__}: functions used in test cases must be defined in an importable module"
        )
    return dumper.represent_name(function)


def _represent_path(dumper: yaml.Dumper, path: pathlib.PurePath) -> yaml.Node:
    """
    Represent a path as ``pathlib.Path``, which loads on any Python version and operating system.

    Parameters
    ----------
    dumper : yaml.Dumper
        The active dumper.
    path : pathlib.PurePath
        Path to represent.

    Returns
    -------
    yaml.Node
        A ``!!python/object/apply:pathlib.Path`` node.
    """
    return dumper.represent_sequence("tag:yaml.org,2002:python/object/apply:pathlib.Path", [path.as_posix()])


_Dumper.add_representer(types.FunctionType, _represent_function)
_Dumper.add_multi_representer(pathlib.PurePath, _represent_path)


def dump_exercise(exercise: dict[str, dict[str, TestSubtask]], to: str | os.PathLike[str] = pathlib.Path("tests")) -> None:
    """
    Dump all subtasks of an exercise to a directory tree.

    Parameters
    ----------
    exercise : dict[str, dict[str, TestSubtask]]
        Nested mapping of task names to subtask dictionaries.
    to : str or os.PathLike, optional
        Target directory, by default ``Path("tests")``.
    """
    to = pathlib.Path(to)
    to.mkdir(parents=True, exist_ok=True)
    for task, subtasks in exercise.items():
        dump_task(subtasks, to=to / task)


def dump_task(subtasks: dict[str, TestSubtask], to: str | os.PathLike[str]) -> None:
    """
    Dump all subtasks of a single task to a directory.

    Parameters
    ----------
    subtasks : dict[str, TestSubtask]
        Mapping of subtask names to ``TestSubtask`` objects.
    to : str or os.PathLike
        Target directory for the YAML files.
    """
    to = pathlib.Path(to)
    to.mkdir(parents=True, exist_ok=True)
    for subtask_name, subtask in subtasks.items():
        dump_subtask(subtask, to=to / f"{subtask_name}.yml")


def dump_subtask(
    subtask: TestSubtask,
    to: str | os.PathLike[str] = pathlib.Path("tests.yml"),
    append: bool = False,
) -> None:
    """
    Dump a single subtask to a YAML file.

    Parameters
    ----------
    subtask : TestSubtask
        The subtask to serialize.
    to : str or os.PathLike, optional
        Target file path, by default ``Path("tests.yml")``.
    append : bool, optional
        Whether to merge into the subtask stored in an existing file, by default False.
        Cases are appended; assertions and prerequisites are added (or replaced by key).
    """
    to = pathlib.Path(to)
    to.parent.mkdir(parents=True, exist_ok=True)
    if append and to.exists():
        with to.open("rb") as f:
            existing = yaml.unsafe_load(f)
        subtask = TestSubtask(
            cases=[*existing.cases, *subtask.cases],
            assertions={**existing.assertions, **subtask.assertions},
            prerequisites={**getattr(existing, "prerequisites", {}), **subtask.prerequisites},
        )
    # sort_keys=False keeps the order of dicts (e.g. inputs), which the expected outputs may depend on
    serialized = yaml.dump(subtask, Dumper=_Dumper, encoding="utf-8", sort_keys=False)
    to.write_bytes(serialized)
