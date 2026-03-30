=============
Student Guide
=============

Your instructor has set up automated tests in your notebook. This guide explains how to
submit your solution, run the tests, and read the results.


Submitting Your Solution
========================

Before the test cell can check your work, you need to register your solution. The submission
cell is usually pre-written by your instructor — just run it after writing your solution.

Functions
---------

If your task asks you to define a function:

.. code-block:: python

   def add(a, b):
       return a + b

The next cell submits it:

.. code-block:: python

   from pytest_nbgrader.loader import Submission
   Submission.submit(add)

You will see a confirmation showing the source code of the submitted function.

Code Strings (Variables)
------------------------

Some exercises ask you to assign variables rather than define a function.
Write your solution in one cell:

.. code-block:: python

   # Your solution
   a, b = b, a

The next cell captures it automatically using ``_i``, which is IPython's way of referring
to the previous cell's source code:

.. code-block:: python

   from pytest_nbgrader.loader import Submission
   Submission.submit(_i)

.. note::

   ``_i`` is a built-in IPython variable that holds the source text of the cell you ran
   immediately before. You don't need to do anything special — just run your solution cell
   first, then the submission cell.

Classes
-------

.. code-block:: python

   class Point:
       def __init__(self, x, y):
           self.x = x
           self.y = y

   Submission.submit(Point)


Running Tests
=============

After submitting, run the test cell that your instructor has prepared. In most nbgrader
courses, this is a **locked cell** (you cannot edit it) that looks something like:

.. code-block:: python

   import pytest

   assert pytest.main([*args, cases / 'values.yml']) is pytest.ExitCode.OK

Just run it. If all tests pass, nothing happens (no error). If a test fails, you will
see an ``AssertionError`` or a test failure message.

Some courses use a simpler format that shows pass/fail counts:

.. code-block:: python

   pytest.main([
       "-qq", "-x",
       "--cases", "tests/TaskName/subtask.yml",
   ])

The flags:

- ``-qq``: minimal output (just pass/fail counts)
- ``-x``: stop on first failure
- ``--cases``: path to the YAML test file provided by your instructor

From the Command Line
---------------------

If you want to run tests outside the notebook:

.. code-block:: console

   $ pytest --cases tests/TaskName/subtask.yml -v


Reading Test Results
====================

Passing Tests
-------------

.. code-block:: text

   2 passed

All test cases matched the expected output.

Failing Tests
-------------

When a test fails, pytest shows what was expected vs. what your code produced:

.. code-block:: text

   FAILED test_assertion[equal_value-0]
     Test case failed:
     2, 3
     The following message was passed:
     Assertion "equal_value" failed with result 2.
     Expected: ((5,), {}),
     Actual: ((6,), {}).

This tells you:

- **Test case inputs**: ``2, 3``
- **Expected output**: ``(5,)`` — the correct return value
- **Actual output**: ``(6,)`` — what your function returned

Errors
------

If your code raises an unexpected exception, the output says:

.. code-block:: text

   Test case could not be tested:
   2, 3
   The following exception was raised:
   ...

Check the traceback to find the bug in your code.


Common Issues
=============

"No data for automatic tests found"
   The ``--cases`` path doesn't point to a valid YAML file.
   Check the file path — it's relative to where pytest runs (usually the notebook directory).

"Submission is None"
   You forgot to call ``Submission.submit()`` before running the tests.
   Go back and run the submission cell first.

Tests pass locally but fail in grading
   Make sure you're not relying on variables defined in earlier cells that aren't part of
   your solution. Your code should work in isolation.

For Advanced Users
==================

If you want to run tests with more control (e.g., in your own scripts or custom notebooks),
you can construct ``pytest.main()`` calls yourself:

.. code-block:: python

   import pytest

   pytest.main([
       "-qq", "-x",
       "-W", "ignore::_pytest.warning_types.PytestAssertRewriteWarning",
       "--cases", "tests/TaskName/subtask.yml",
   ])

Or use the ``runner`` convenience wrapper:

.. code-block:: python

   from pytest_nbgrader.runner import main
   main(task="TaskName", subtask="subtask")
