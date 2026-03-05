"""Serialize test cases to YAML files."""

import pathlib

import yaml

from pytest_nbgrader.cases import TestSubtask


def dump_exercise(exercise: dict[str, dict[str, TestSubtask]], to=pathlib.Path("tests")):
    """
    Dump all subtasks of an exercise to a directory tree.

    Parameters
    ----------
    exercise : dict[str, dict[str, TestSubtask]]
        Nested mapping of task names to subtask dictionaries.
    to : pathlib.Path, optional
        Target directory, by default ``Path("tests")``.
    """
    to.mkdir(parents=True, exist_ok=True)
    for task, subtasks in exercise.items():
        dump_task(subtasks, to=to / task)


def dump_task(subtasks: dict[str, TestSubtask], to: pathlib.Path):
    """
    Dump all subtasks of a single task to a directory.

    Parameters
    ----------
    subtasks : dict[str, TestSubtask]
        Mapping of subtask names to ``TestSubtask`` objects.
    to : pathlib.Path
        Target directory for the YAML files.
    """
    to.mkdir(parents=True, exist_ok=True)
    for subtask_name, subtask in subtasks.items():
        dump_subtask(subtask, to=to / f"{subtask_name}.yml")


def dump_subtask(
    subtask: TestSubtask,
    to: pathlib.Path = pathlib.Path("tests.yml"),
    append=False,
):
    """
    Dump a single subtask to a YAML file.

    Parameters
    ----------
    subtask : TestSubtask
        The subtask to serialize.
    to : pathlib.Path, optional
        Target file path, by default ``Path("tests.yml")``.
    append : bool, optional
        Whether to append to an existing file, by default False.
    """
    to.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" + append * "+"
    with pathlib.Path(to).open(mode) as f:
        yaml.dump(subtask, f, encoding="utf-8")
