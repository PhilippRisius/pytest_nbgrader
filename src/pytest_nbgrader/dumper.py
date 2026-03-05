import pathlib

import yaml

from pytest_nbgrader.cases import TestSubtask


def dump_exercise(exercise: dict[str, dict[str, TestSubtask]], to=pathlib.Path("tests")):
    to.mkdir(parents=True, exist_ok=True)
    for task, subtasks in exercise.items():
        dump_task(subtasks, to=to / task)


def dump_task(subtasks: dict[str, TestSubtask], to: pathlib.Path):
    to.mkdir(parents=True, exist_ok=True)
    for subtask_name, subtask in subtasks.items():
        dump_subtask(subtask, to=to / f"{subtask_name}.yml")


def dump_subtask(
    subtask: TestSubtask,
    to: pathlib.Path = pathlib.Path("tests.yml"),
    append=False,
):
    to.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" + append * "+"
    with pathlib.Path(to).open(mode) as f:
        yaml.dump(subtask, f, encoding="utf-8")
