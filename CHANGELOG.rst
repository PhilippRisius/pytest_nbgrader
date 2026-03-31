=========
Changelog
=========

..
    `Unreleased <https://github.com/PhilippRisius/pytest_nbgrader>`_ (latest)
    -------------------------------------------------------------------------

    Contributors:

    Changes
    ^^^^^^^
    * No change.

    Fixes
    ^^^^^
    * No change.

.. _changes_0.3.0:

`v0.3.0 <https://github.com/PhilippRisius/pytest_nbgrader/tree/v0.3.0>`_ (2026-03-31)
----------------------------------------------------------------------------------------

Contributors: Philipp Emmo Tobias Risius (:user:`PhilippRisius`)

Changes
^^^^^^^
* Added inline type annotations to all source modules (``from __future__ import annotations``).
* Added ``__all__`` exports to all 9 source modules, defining the public API explicitly.
* Added comprehensive test suite: 77 assertion tests, 44 cases/dumper/loader tests, 23 harness/conftest/runner tests, 11 end-to-end workflow tests (213 total, up from 19).
* Added usage documentation with quickstart guide, instructor guide, student guide, and assertions reference.
* Cleaned up ``pyproject.toml``: removed stale classifiers, unused dependencies, dead flit.sdist entries, and duplicate mypy blocks.
* Cleaned up ruff ignores: removed 9 suppressions, reduced per-file-ignores to inherent code patterns only.
* Renamed project display to pytest-nbgrader, fixed badges and README.
* Configured Coveralls integration for coverage reporting.

Fixes
^^^^^
* Fixed ``has_import``: 4 bugs (missing ``outputs`` parameter, ``case.return_object`` usage, ``relative_to()`` crash on stdlib modules, inconsistent return tuples). Now works through the standard harness pipeline.
* Fixed ``equal_attributes``: inverted logic was returning ``TESTS_FAILED`` when attributes matched.
* Fixed ``has_method`` and ``calls``: missing ``@_log`` decorator, used ``case.return_object`` instead of ``outputs`` parameter.
* Fixed ``dump_subtask`` append mode: ``"wb+"`` truncated instead of appending; now uses ``"ab"``.
* Fixed ``writes()`` unchecked stream comparison: loop compared all streams including those with ``expected=None``, causing false failures.
* Fixed ``file_contents`` signature to match ``_log`` wrapper contract.

.. _changes_0.2.0:

`v0.2.0 <https://github.com/PhilippRisius/pytest_nbgrader/tree/v0.2.0>`_ (2026-03-23)
----------------------------------------------------------------------------------------

Contributors: Philipp Emmo Tobias Risius (:user:`PhilippRisius`)

Changes
^^^^^^^
* Integrated full plugin code into package structure (loader, harness, assertions, prerequisites, runner, dumper).

Fixes
^^^^^
* No change.

.. _changes_0.1.0:

`v0.1.0 <https://github.com/PhilippRisius/pytest_nbgrader/tree/v0.1.0>`_ (2025-04-09)
----------------------------------------------------------------------------------------

Contributors: Philipp Emmo Tobias Risius (:user:`PhilippRisius`)

Changes
^^^^^^^
* First release on PyPI.
