===========
Quick Start
===========

This walkthrough shows the complete pytest-nbgrader workflow end-to-end: an instructor
creates test cases, a student submits a solution, and pytest grades it automatically.
It is a good starting point whether you want to evaluate the plugin or understand how
the pieces fit together.


A Complete Example
==================

We will create a graded exercise for a simple ``add`` function: define test cases,
serialize them, submit a solution, and run the tests.


Step 1: Create Test Cases (Instructor)
--------------------------------------

In a data generation notebook or script, define the test cases and serialize them:

.. code-block:: python

   from pathlib import Path
   from pytest_nbgrader.assertions import equal_value
   from pytest_nbgrader.cases import TestCase, TestSubtask
   from pytest_nbgrader.dumper import dump_subtask

   subtask = TestSubtask(
       cases=[
           TestCase(inputs=((2, 3), {}), expected=((5,), {})),
           TestCase(inputs=((0, -1), {}), expected=((-1,), {})),
       ],
       assertions={equal_value: ((), {})},
   )

   dump_subtask(subtask, to=Path("tests/Addition/basic.yml"))

Each ``TestCase`` specifies:

- **inputs**: ``(positional_args, keyword_args)`` passed to the student's function
- **expected**: ``(expected_return_values, expected_named_outputs)`` to compare against

The ``assertions`` dict maps assertion functions to their extra arguments.
Here, ``equal_value`` checks for exact equality and needs no extra arguments.

Running this creates ``tests/Addition/basic.yml`` containing the serialized test data.


Step 2: Submit a Solution (Student)
------------------------------------

In a notebook cell, students define their solution and submit it:

.. code-block:: python

   from pytest_nbgrader.loader import Submission

   def add(a, b):
       return a + b

   Submission.submit(add)

This prints a confirmation:

.. code-block:: text

   The following submission will be tested:

   def add(a, b):
       return a + b


Step 3: Run the Tests (Student)
-------------------------------

In the next cell, run pytest with the ``--cases`` flag pointing to the YAML file:

.. code-block:: python

   import pytest

   pytest.main([
       "-qq", "-x",
       "-W", "ignore::_pytest.warning_types.PytestAssertRewriteWarning",
       "--cases", "tests/Addition/basic.yml",
   ])

If the solution is correct, the output shows:

.. code-block:: text

   2 passed

If a test fails, pytest reports which case failed and what was expected vs. actual.


How It Works
============

pytest-nbgrader has three stages: **submit**, **execute**, and **assert**.

.. code-block:: text

   Student code                  YAML file                    pytest output
   ─────────────                 ─────────                    ─────────────
   def add(a, b):    submit()   tests/Addition/basic.yml     2 passed
       return a + b  ────────►  (TestSubtask with cases)  ──────────────►
                                                    │
                                             for each case:
                                               execute(case, submission)
                                                    │
                                             for each assertion:
                                               assertion(case, outputs)

1. **Submit**: ``Submission.submit()`` stores the student's function (or code string, or class)
   in a global singleton. This makes it available to the pytest plugin without passing it
   through files.

2. **Execute**: When pytest runs, the plugin loads the YAML file and reconstructs the
   ``TestSubtask``. For each ``TestCase``, it calls the submitted function with the case's
   inputs and captures the outputs. The execution is dispatched by submission type — functions
   are called directly, code strings are passed to ``exec()``, classes are instantiated.

3. **Assert**: Each assertion function compares the actual outputs against the expected values.
   The plugin parametrizes tests as ``cases × assertions``, so two cases with one assertion
   creates two test nodes; three cases with two assertions creates six.

This separation of concerns — test *data* in YAML, test *logic* in assertion functions — means
instructors can reuse the same assertions across hundreds of exercises while varying only the
inputs and expected outputs.


Next Steps
----------

- **Instructors**: See the :doc:`instructor-guide` for test case design, assertions, prerequisites, YAML serialization, and nbgrader integration.
- **Students**: See the :doc:`student-guide` for submitting solutions and reading test output.
- **Reference**: See the :doc:`assertions-reference` for all available assertion functions.
