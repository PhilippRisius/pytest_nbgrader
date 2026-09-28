=========
Changelog
=========

`Unreleased <https://github.com/PhilippRisius/pytest_nbgrader>`_ (latest)
-------------------------------------------------------------------------

Contributors: Philipp Emmo Tobias Risius (:user:`PhilippRisius`)

Changes
^^^^^^^
* ``equal_attributes`` and ``close_attributes`` compare every object in ``outputs[0]`` with the corresponding object in ``case.expected[0]`` (one per instantiation of a class), and fail if the numbers differ. Previously only the first instance was checked.
* ``equal_contents`` casts only containers to the expected type; scalars are compared as they are. Missing or extra outputs fail.
* ``almost_equal`` requires actual and expected values to have the same shape instead of broadcasting.
* ``raises=True`` cases may be mixed with other cases: the built-in value assertions are not applied to the raised exception. Custom assertions still receive it, unless they set ``accepts_exceptions = False``.
* ``execute()`` always returns a tuple of positional outputs: a function returning ``None`` with one expected output gives ``(None,)``; with several expected outputs, tuples, lists and numpy arrays hold one output per element, other values (including strings) are one output. Memoized functions, ``functools.partial`` and other callables can be submitted.
* Code strings run with ``__name__ == "__main__"``; dunder names are not part of the output scope.
* The harness accepts prerequisites and assertions keyed by a label, ``{"label": (function, (args, kwargs))}``, as documented. Test ids name the assertion and case (``test_assertion[equal_value-0]``).
* ``runner.main(auto=False)`` runs only the tests passed in ``*args``.
* ``writes`` and ``writes_file`` accept ``argv``; ``sys.exit(0)`` counts as a normal run.
* ``dump_subtask`` keeps dict order, merges into the existing subtask with ``append=True``, writes portable ``pathlib.Path`` tags, accepts ``str`` paths, and refuses functions that students cannot import by module and name (lambdas, methods, ``__main__``). Requires PyYAML >= 5.1.
* ``time_bounds`` bounds are inclusive; ``0`` is a bound, not "unbounded".
* Failure messages name the exit code (``TESTS_FAILED``); ``-v`` shows the full traceback.
* ``has_signature`` accepts a submission whose raw or evaluated (postponed) annotations match the reference.
* Configuration errors (missing or invalid ``--cases`` file, subtask without cases or assertions, no submission) are reported as such.

Fixes
^^^^^
* Fixed false passes: ``equal_contents`` for functions returning nothing or too few values; ``raises`` counting the plugin's own errors as the expected exception; ``almost_equal`` for wrong-shaped answers; ``equal_attributes`` for wrong later instances and misspelled attributes; subtasks without cases or assertions.
* Fixed correct submissions failing: numpy arrays in ``equal_value``; ``close_attributes`` in the harness; value assertions on ``raises=True`` cases; the documented prerequisites format; ``writes_file`` reporting ``__pycache__`` files and read files; ``sys.exit(0)`` and ``argparse`` scripts in ``writes``; module submissions using dataclasses with postponed annotations; ``dump_subtask`` reordering dict inputs.
* Fixed crashes: ``format_result`` for class submissions; scalar return values in ``execute()``; ``SystemExit`` from student code breaking later cases; missing variables, attributes and files reported as internal errors; ``has_import`` positional paths.
* Fixed the plugin warning in every pytest run of unrelated projects, which broke suites using ``-W error``.
* Fixed ``runner.main`` leaking symlinks after errors or interrupted runs, failing on re-runs from another directory, and rejecting falsy submissions.
* Fixed ``writes``/``writes_file`` leaving the shared submission renamed when the module raised.
* Fixed a failed ``Submission.submit()`` keeping the previous submission.
* Fixed CI linting (unpinned ruff with preview rules), coverage measurement, sdist contents, ``make release``, and several workflow configuration issues.

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
