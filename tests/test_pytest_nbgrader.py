#!/usr/bin/env python
"""Tests for `pytest_nbgrader` package."""

import pathlib
from importlib.util import find_spec


def test_package_metadata():
    """Test the package metadata."""
    project = find_spec("pytest_nbgrader")

    assert project is not None
    assert project.submodule_search_locations is not None
    location = project.submodule_search_locations[0]

    metadata = pathlib.Path(location).resolve().joinpath("__init__.py")

    with metadata.open() as f:
        contents = f.read()
        assert """Philipp Emmo Tobias Risius""" in contents
        assert '__email__ = "philipp.e.risius@theo.physik.uni-giessen.de"' in contents
        assert '__version__ = "0.2.0"' in contents


def test_package_reexports():
    """Test that __init__.py re-exports harness and loader."""
    import pytest_nbgrader

    assert hasattr(pytest_nbgrader, "harness")
    assert hasattr(pytest_nbgrader, "loader")
    assert hasattr(pytest_nbgrader.loader, "Submission")
    assert hasattr(pytest_nbgrader.harness, "TestClass")


def test_import_loader():
    """Test that the loader module is importable."""
    from pytest_nbgrader import loader

    assert hasattr(loader, "Submission")
    assert hasattr(loader.Submission, "submit")


def test_import_cases():
    """Test that the cases module is importable."""
    from pytest_nbgrader import cases

    assert hasattr(cases, "TestCase")
    assert hasattr(cases, "TestSubtask")
    assert hasattr(cases, "execute")


def test_import_harness():
    """Test that the harness module is importable."""
    from pytest_nbgrader import harness

    assert hasattr(harness, "TestClass")


def test_import_assertions():
    """Test that the assertions module is importable."""
    from pytest_nbgrader import assertions

    assert hasattr(assertions, "equal_value")
    assert hasattr(assertions, "almost_equal")
    assert hasattr(assertions, "raises")


def test_import_prerequisites():
    """Test that the prerequisites module is importable."""
    from pytest_nbgrader import prerequisites

    assert hasattr(prerequisites, "has_signature")
    assert hasattr(prerequisites, "writes")


def test_import_dumper():
    """Test that the dumper module is importable."""
    from pytest_nbgrader import dumper

    assert hasattr(dumper, "dump_exercise")
    assert hasattr(dumper, "dump_subtask")


def test_import_runner():
    """Test that the runner module is importable."""
    from pytest_nbgrader import runner

    assert hasattr(runner, "main")
