=================
Instructor Guide
=================

This guide covers how to create test cases, choose assertions, serialize to YAML,
write custom test harnesses, and integrate with nbgrader's assignment pipeline.


Defining Test Cases
===================

A ``TestCase`` stores one set of inputs and the corresponding expected outputs:

.. code-block:: python

   from pytest_nbgrader.cases import TestCase

   case = TestCase(
       inputs=((2, 3), {}),
       expected=((5,), {}),
   )

Both ``inputs`` and ``expected`` are ``(positional_args, keyword_args)`` tuples.
The exact format depends on the submission type.

Function Inputs
---------------

For function submissions, ``inputs`` holds the arguments passed to the function:

.. code-block:: python

   # Tests: add(2, 3) == 5
   TestCase(inputs=((2, 3), {}), expected=((5,), {}))

   # Tests: greet(name="Alice") == "Hello, Alice"
   TestCase(inputs=((), {"name": "Alice"}), expected=(("Hello, Alice",), {}))

The expected positional tuple wraps the return value — a function returning ``5`` expects ``(5,)``.

Code String Inputs
------------------

For code string submissions (variable assignments), inputs are keyword arguments that become
the execution scope, and expected outputs are the variables that should exist after execution:

.. code-block:: python

   # Student code: "result = x + y"
   # Test: with x=10, y=20, result should be 30
   TestCase(
       inputs=((), {"x": 10, "y": 20}),
       expected=((), {"x": 10, "y": 20, "result": 30}),
   )

.. note::

   The expected dict must include the input variables too, because they remain in scope
   after execution.

Class Inputs
------------

For class submissions, ``inputs`` is a **list** of ``(args, kwargs)`` pairs — one per
instantiation:

.. code-block:: python

   # Instantiate Point(1, 2) and Point(3, 4)
   TestCase(
       inputs=[((1, 2), {}), ((3, 4), {})],
       expected=((Point(1, 2), Point(3, 4)), {}),
   )

``expected`` holds one reference object per instantiation. The resulting objects are compared
pairwise using attribute assertions like ``equal_attributes`` or ``close_attributes``; a
different number of objects fails.

.. note::

   The reference objects are stored with their attributes and class name, so their class must
   be importable when the YAML file is loaded — define it in a module that ships with the
   tests rather than in the data generation notebook.

Testing Exceptions
------------------

To test that code raises an exception, set ``raises=True``:

.. code-block:: python

   TestCase(
       inputs=((1, 0), {}),
       expected=((), {}),
       raises=True,
   )

Use the ``raises`` assertion to verify the exception type (see :doc:`assertions-reference`).
``raises=True`` cases may share a subtask with ordinary cases: other assertions (such as
``equal_value``) are not applied to the exception, and a submission that does not raise
fails the ``raises`` assertion.

Timing Constraints
------------------

To check execution time bounds:

.. code-block:: python

   TestCase(
       inputs=((large_input,), {}),
       expected=((result,), {}),
       timing=(None, 2.0),  # must finish within 2 seconds
   )

Use with the ``time_bounds`` assertion. The time is checked after the call returns: code that
never finishes is not interrupted by pytest-nbgrader, only by nbgrader's cell timeout.


Choosing Assertions
===================

Assertions verify the relationship between expected and actual outputs.
Each assertion function takes ``(case, outputs, *args, **kwargs)`` and returns
``(ExitCode.OK, "")`` on success or ``(ExitCode.TESTS_FAILED, error_info)`` on failure.

For Functions
-------------

- :func:`~pytest_nbgrader.assertions.equal_value` — exact equality of return values
- :func:`~pytest_nbgrader.assertions.almost_equal` — approximate equality for floats (numpy-based, with ``atol``/``rtol``)
- :func:`~pytest_nbgrader.assertions.raises` — expected exception was raised (use with ``TestCase(raises=True)``)
- :func:`~pytest_nbgrader.assertions.time_bounds` — execution time within ``TestCase.timing`` bounds

For Code Strings
----------------

- :func:`~pytest_nbgrader.assertions.equal_value` — exact equality of named variables (pass variable names as ``*args``)
- :func:`~pytest_nbgrader.assertions.equal_scope` — the set of variable names matches the expected scope exactly (extra helper variables or imports fail)
- :func:`~pytest_nbgrader.assertions.equal_types` — variables are instances of the expected types (subclasses pass, e.g. ``bool`` where ``int`` is expected)
- :func:`~pytest_nbgrader.assertions.almost_equal` — approximate equality of named variables

For Classes
-----------

- :func:`~pytest_nbgrader.assertions.equal_attributes` — attribute values match between expected and actual instances
- :func:`~pytest_nbgrader.assertions.close_attributes` — attribute values approximately match (numpy-based)
- :func:`~pytest_nbgrader.assertions.has_method` — object has required methods or attributes

For File Output
---------------

- :func:`~pytest_nbgrader.assertions.file_contents` — written files match expected contents byte-for-byte

See :doc:`assertions-reference` for complete signatures and examples.


Adding Prerequisites
====================

Prerequisites validate the submission before test cases run. They are optional — in many
courses, assertions alone are sufficient.

Signature Validation
--------------------

Verify that a student's function has the correct parameter names:

.. code-block:: python

   import inspect
   from pytest_nbgrader.prerequisites import has_signature

   ref_sig = inspect.signature(lambda a, b: None)

   subtask = TestSubtask(
       cases=[...],
       assertions={...},
       prerequisites={"signature": (has_signature, ((ref_sig,), {}))},
   )

``has_signature`` compares parameter names, and optionally types, defaults, and return
annotations via the ``*strict_comparisons`` and ``**comparisons`` arguments.

The prerequisites dict maps a label (used as the test id) to ``(function, (args, kwargs))``.
Like assertions, it may also be keyed by the function itself:
``prerequisites={has_signature: ((ref_sig,), {})}``.

Module Output Checking
----------------------

For path/module submissions, verify stdout/stderr output during import:

.. code-block:: python

   from pytest_nbgrader.prerequisites import writes

   prerequisites={"output": (writes, ((), {"out": "Hello, World!\n"}))}

Pass ``name="__main__"`` to run the module as a script (its ``if __name__ == "__main__":``
block runs) and ``argv=[...]`` for its command line arguments. ``sys.exit(0)`` counts as a
normal run; a non-zero exit status fails.

File Write Checking
-------------------

Verify which files a module creates, deletes, or modifies during import:

.. code-block:: python

   from pathlib import Path
   from pytest_nbgrader.prerequisites import writes_file

   prerequisites={"files": (writes_file, ((), {"created": {Path("output.txt")}}))}

Paths are relative to the directory pytest runs in; ``created``, ``deleted`` and ``modified``
must match exactly. Files in ``__pycache__`` directories are ignored.


Packaging with TestSubtask
==========================

A ``TestSubtask`` bundles test cases with assertions and prerequisites:

.. code-block:: python

   from pytest_nbgrader.assertions import almost_equal, equal_value
   from pytest_nbgrader.cases import TestCase, TestSubtask

   subtask = TestSubtask(
       cases=[
           TestCase(inputs=((2, 3), {}), expected=((5,), {})),
           TestCase(inputs=((0, 0), {}), expected=((0,), {})),
       ],
       assertions={equal_value: ((), {})},
   )

The Assertions Dict
-------------------

The ``assertions`` dict maps **assertion function objects** to their extra arguments:

.. code-block:: python

   assertions = {
       equal_value: (("a", "b"), {}),              # check variables a, b for equality
       almost_equal: (("x",), {"atol": 1e-6}),     # check x with tolerance
   }

The format is ``{function: (extra_positional_args, extra_keyword_args)}``.
The ``case`` and ``outputs`` arguments are passed automatically by the harness.

When pytest runs, each case is tested against **each** assertion, creating a
Cartesian product of ``len(cases) × len(assertions)`` test nodes, plus one node per
prerequisite (a single skipped node if there are none). A subtask needs at least one case and
one assertion (or a prerequisite); otherwise the run fails instead of passing vacuously.

Functions used in assertions and prerequisites must be importable by the students' kernels:
define custom assertions in a module, not in the data generation notebook. The dumper refuses
lambdas and functions defined in ``__main__``.

Generating Test Cases Programmatically
--------------------------------------

For robust grading, generate many test cases from parameter spaces:

.. code-block:: python

   import itertools
   from pytest_nbgrader.assertions import equal_value, equal_types
   from pytest_nbgrader.cases import TestCase, TestSubtask

   left = (1, 2.0, True, "xyz")
   right = (3, 4.0, False, "abc")

   cases = [
       TestCase(
           inputs=((), {"a": x, "b": y}),
           expected=((), {"a": y, "b": x}),
       )
       for x, y in itertools.product(left, right)
   ]

   assertions = {
       equal_value: (("a", "b"), {}),
       equal_types: (("a", "b"), {}),
   }

   subtask = TestSubtask(cases=cases, assertions=assertions)

This creates 16 test cases × 2 assertions = 32 test nodes.


Serializing to YAML
====================

Test cases are serialized to YAML for distribution to students.

Single Subtask
--------------

.. code-block:: python

   from pathlib import Path
   from pytest_nbgrader.dumper import dump_subtask

   dump_subtask(subtask, to=Path("tests/Addition/basic.yml"))

Full Exercise
-------------

For multi-task exercises, organize subtasks into a nested dict and use ``dump_exercise``:

.. code-block:: python

   from pytest_nbgrader.dumper import dump_exercise

   exercise = {
       "Addition": {
           "basic": subtask_basic,
           "edge_cases": subtask_edge,
       },
       "Multiplication": {
           "correctness": subtask_mul,
       },
   }

   dump_exercise(exercise)

This creates the directory tree:

.. code-block:: text

   tests/
     Addition/
       basic.yml
       edge_cases.yml
     Multiplication/
       correctness.yml

What the YAML Looks Like
-------------------------

A serialized YAML file contains the full ``TestSubtask`` — assertions, cases, and metadata —
using Python-specific YAML tags:

.. code-block:: yaml

   !!python/object:pytest_nbgrader.cases.TestSubtask
   cases:
   - !!python/object:pytest_nbgrader.cases.TestCase
     inputs: !!python/tuple
     - !!python/tuple []
     - a: 1
       b: 2
     expected: !!python/tuple
     - !!python/tuple []
     - a: 2
       b: 1
     raises: false
     timing: !!python/tuple
     - null
     - null
   assertions:
     ? !!python/name:pytest_nbgrader.assertions.equal_value ''
     : !!python/tuple
     - !!python/tuple
       - a
       - b
     - {}
   prerequisites: {}

The ``!!python/object`` and ``!!python/name`` tags let ``yaml.unsafe_load()`` reconstruct
the original Python objects at load time. You don't need to read or edit these files — they
are generated by the dumper and consumed by the plugin automatically.

.. warning::

   YAML files are loaded using ``yaml.unsafe_load()``, which can execute arbitrary Python
   code during deserialization. **Only distribute YAML files through trusted channels**
   (e.g., your institution's LMS or nbgrader's exchange directory). Students should never
   load YAML files from untrusted sources.

.. note::

   The YAML files contain every expected output in plain text, and students receive them.
   The tests also run in the student's own kernel, so they are a self-check rather than a
   tamper-proof exam. Keep hidden test cases out of ``release/`` and review submissions.


Writing Custom Test Harnesses
=============================

For exercises that need custom logic beyond the standard assertion pipeline — such as testing
class methods, generators, or complex object interactions — write a Python test file alongside
the YAML data.

.. code-block:: python

   # tests/MyTask/test_mytask.py
   import pytest
   from pytest_nbgrader.assertions import close_attributes
   from pytest_nbgrader.cases import format_result

   class TestCircle:
       """Custom test harness for Circle class."""

       def test_instantiation(self, submission, cases, verbosity):
           args, kwargs = cases.inputs[0]
           instance = submission(*args, **kwargs)
           result, message = close_attributes(
               cases, instance, "radius", "area", "circumference",
               atol=1e-6, rtol=1e-6,
           )
           if result is not pytest.ExitCode.OK:
               pytest.fail(format_result(cases.inputs[0], result, message))

Here ``cases.expected`` holds the reference object, e.g. ``expected=((Circle(1.0),), {})``.
Give each harness file a unique name: with pytest's default import mode, two files named
``tests.py`` in different task directories cannot both be imported in the same kernel.

In the student notebook, run the custom harness with the YAML data:

.. code-block:: python

   pytest.main([
       "-qq", "-x",
       "--cases", "tests/MyTask/data.yml",
       "tests/MyTask/test_mytask.py::TestCircle",
   ])

Since a test path is given, only the custom harness runs; ``data.yml`` needs no assertions.
To run the YAML assertions as well, pass the path to ``runner.main()`` (see below).


Using ``runner.main()``
=======================

The ``runner`` module provides a convenience wrapper around ``pytest.main()`` that handles
path construction, temporary symlinks to the harness and conftest, and the standard flags:

.. code-block:: python

   from pytest_nbgrader.runner import main

   main(task="Addition", subtask="basic")

This is equivalent to:

.. code-block:: python

   pytest.main([
       "-p", "no:pytest-nbgrader",
       "--noauto",
       "-W", "ignore::pytest.PytestAssertRewriteWarning",
       "--cases=tests/Addition/basic.yml",
       "harness.py::TestClass",
   ])

``runner.main()`` creates temporary symlinks to the built-in ``harness.py`` and ``conftest.py``
in the current directory, runs pytest, then cleans up. It accepts additional ``*args`` that are
forwarded to ``pytest.main()``, e.g. the path of a custom harness. With ``auto=False`` the
built-in test class is not run, only the tests given in ``*args``.

.. note::

   The example course uses raw ``pytest.main()`` calls for more control over flags and paths.
   Use ``runner.main()`` when the default harness and conftest are sufficient and you want
   a simpler API.


Integrating with nbgrader
==========================

pytest-nbgrader works alongside nbgrader's assignment pipeline. This section explains how to
set up a course so that test cases flow correctly from instructor to student.

How the Pipeline Works
----------------------

nbgrader's ``generate_assignment`` command copies notebooks from ``source/`` to ``release/``,
applying preprocessors that clear solutions, lock cells, and strip hidden tests. Critically,
**non-notebook files are copied as-is** — this includes the ``tests/`` directory with your
YAML files.

The flow:

.. code-block:: text

   source/{assignment}/              nbgrader generate_assignment
     _data_generation.ipynb  ────────────── (excluded by config)
     exercise.ipynb          ──────────────► release/{assignment}/exercise.ipynb
     tests/                  ──────────────► release/{assignment}/tests/
       Task/subtask.yml                        Task/subtask.yml

Students receive the release version. After submission, nbgrader collects notebooks into
``submitted/``, then ``autograde`` runs them in ``autograded/``. The ``tests/`` directory
must be present at each stage for pytest to find the YAML files.

Directory Layout
----------------

A typical course directory:

.. code-block:: text

   HomeworkAssignments/
     nbgrader_config.py
     source/
       02_arithmetics/
         _data_generation.ipynb     # instructor-only: generates YAML
         exchange_variables.ipynb   # notebook with solution + test cells
         tests/
           ExchangeVariables/
             test_for_equal_value.yml
             test_for_equal_types.yml
     release/                       # generated by nbgrader
       02_arithmetics/
         exchange_variables.ipynb   # solutions cleared, cells locked
         tests/                     # copied as-is from source
           ExchangeVariables/
             test_for_equal_value.yml

The ``source/`` directory is instructor-only. It contains:

- **Data generation notebooks** (prefixed with ``_``) that create the YAML test files
- **Assignment notebooks** with model solutions in solution cells and pre-built test cells
- **tests/** directories with the serialized YAML output

Configuring nbgrader
--------------------

Use ``nbgrader_config.py`` to prevent instructor-only files from leaking to students:

.. code-block:: python

   c = get_config()

   c.CourseDirectory.ignore = [
       '*data_generation*.ipynb',  # data generation notebooks
       '_*',                       # any file/dir starting with _
       '.ipynb_checkpoints',
       '*.pyc',
       '__pycache__',
       '.pytest_cache',
   ]

   # Only process notebooks not starting with _
   c.CourseDirectory.notebook_id = '[!_]*'

The ``ignore`` list ensures ``_data_generation.ipynb`` and ``_model_solutions/`` directories
are excluded from ``generate_assignment``. The ``notebook_id`` pattern provides an additional
safeguard — only non-underscored notebooks are treated as assignment notebooks.

Writing Test Cells in Notebooks
-------------------------------

In the source notebook, write the test cells alongside the solution. These cells will be
**locked** (read-only) in the released version so students cannot modify them.

A typical pattern uses two cells. The first submits the student's solution and sets up
shared arguments:

.. code-block:: python

   import pathlib
   import pytest
   from pytest_nbgrader import loader

   loader.Submission.submit(_i)
   cases = pathlib.Path('tests') / 'TaskName'
   args = ['-qq', '-x',
           '-W', 'ignore::_pytest.warning_types.PytestAssertRewriteWarning',
           '--cases']

The second cell runs the actual tests:

.. code-block:: python

   assert pytest.main([*args, cases / 'equal_value.yml']) is pytest.ExitCode.OK
   assert pytest.main([*args, cases / 'equal_types.yml']) is pytest.ExitCode.OK

The ``assert ... is pytest.ExitCode.OK`` pattern makes the cell raise an ``AssertionError``
if any test fails, which nbgrader's autograder interprets as a failed grade cell.

In nbgrader, mark these cells with the appropriate metadata:

- Set **locked: true** so students cannot edit the test cells
- Set **grade: true** and assign points for cells that should be autograded
- Set **solution: true** on the cell where students write their answer

.. tip::

   Use ``_i`` (IPython's magic variable for the previous cell's source code) to capture
   code string submissions. This avoids asking students to wrap their code in quotes —
   they just write normal Python in the solution cell, and the next cell captures it
   automatically.

Data Generation Workflow
------------------------

The data generation notebook is the instructor's workspace for creating test cases. A typical
workflow:

1. **Import** assertion functions, ``TestCase``, ``TestSubtask``, and the dumper
2. **Define** model solution functions that compute expected outputs
3. **Generate** test cases from parameter combinations (e.g., with ``itertools.product``)
4. **Package** into ``TestSubtask`` objects with appropriate assertions
5. **Serialize** with ``dump_exercise()`` — output goes to ``tests/`` alongside the notebook

.. code-block:: python

   import itertools
   from pytest_nbgrader.assertions import equal_value, equal_types
   from pytest_nbgrader.cases import TestCase, TestSubtask
   from pytest_nbgrader import dumper

   left = (1, 2.0, True, 'xyz')
   right = (3, 4.0, False, 'abc')

   cases = [
       TestCase(
           inputs=((), {"a": x, "b": y}),
           expected=((), {"a": y, "b": x}),
       )
       for x, y in itertools.product(left, right)
   ]

   exercise = {
       "ExchangeVariables": {
           "equal_value": TestSubtask(
               cases=cases,
               assertions={equal_value: (("a", "b"), {})},
           ),
           "equal_types": TestSubtask(
               cases=cases,
               assertions={equal_types: (("a", "b"), {})},
           ),
       },
   }

   dumper.dump_exercise(exercise)

Run this notebook once to populate the ``tests/`` directory. Then run
``nbgrader generate_assignment`` to produce the student-facing release — the YAML files
are copied automatically.
