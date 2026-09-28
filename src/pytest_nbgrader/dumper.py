"""Serialize test cases to YAML files."""

from __future__ import annotations


__all__ = ["dump_exercise", "dump_subtask", "dump_task"]

import importlib
import os
import pathlib
import sys
import types
from collections.abc import Mapping, Sequence

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
        If the function cannot be imported by its module and name, e.g. a lambda, a local
        function, a method, or a function defined in ``__main__`` (which would resolve to the
        student's namespace when loaded).
    """
    module_name, qualname = function.__module__, function.__qualname__
    importable = module_name != "__main__" and "<" not in qualname
    if importable:
        # PyYAML writes <module>.<__name__>, which must resolve to the same function when loaded
        try:
            module = sys.modules.get(module_name) or importlib.import_module(module_name)
        except ImportError:
            importable = False
        else:
            importable = getattr(module, function.__name__, None) is function
    if not importable:
        raise yaml.representer.RepresenterError(
            f"cannot dump {module_name}.{qualname}: functions used in test cases must be defined at the top level of an importable module"
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


def _merged(existing: Mapping | Sequence, new: Mapping | Sequence) -> dict | list:
    """
    Merge prerequisites or assertions, given as dicts or as lists of ``(key, value)`` pairs.

    Parameters
    ----------
    existing : Mapping or Sequence
        Stored items.
    new : Mapping or Sequence
        Items to add; they replace stored items with the same key if both are dicts.

    Returns
    -------
    dict or list
        The merged items: a dict if both are dicts, otherwise a list of pairs.
    """
    if isinstance(existing, Mapping) and isinstance(new, Mapping):
        return {**existing, **new}
    return [*(existing.items() if isinstance(existing, Mapping) else existing), *(new.items() if isinstance(new, Mapping) else new)]


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
            assertions=_merged(existing.assertions, subtask.assertions),
            prerequisites=_merged(getattr(existing, "prerequisites", {}), subtask.prerequisites),
        )
    # sort_keys=False keeps the order of dicts (e.g. inputs), which the expected outputs may depend on
    serialized = yaml.dump(subtask, Dumper=_Dumper, encoding="utf-8", sort_keys=False)
    to.write_bytes(serialized)
