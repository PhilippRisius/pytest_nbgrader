====================
Assertions Reference
====================

All assertion functions follow the same pattern: they take ``(case, outputs, *args, **kwargs)``
and return ``(pytest.ExitCode.OK, "")`` on success or ``(pytest.ExitCode.TESTS_FAILED, error_info)``
on failure. The ``case`` and ``outputs`` arguments are supplied automatically by the harness;
the ``*args`` and ``**kwargs`` come from the assertions dict in your ``TestSubtask``.


Summary
=======

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Function
     - Purpose
     - Typical Submission Type
   * - ``equal_value``
     - Exact equality
     - Function, code string
   * - ``almost_equal``
     - Approximate equality (numpy)
     - Function, code string
   * - ``equal_scope``
     - Same variable names in scope
     - Code string
   * - ``equal_types``
     - Same types for named variables
     - Code string
   * - ``equal_contents``
     - Container contents match (with type coercion)
     - Code string, function
   * - ``raises``
     - Expected exception was raised
     - Function (with ``raises=True``)
   * - ``file_contents``
     - Written file contents match
     - Path/module
   * - ``time_bounds``
     - Execution time within bounds
     - Any
   * - ``equal_attributes``
     - Object attribute values match
     - Class
   * - ``close_attributes``
     - Object attributes approximately match
     - Class
   * - ``has_method``
     - Object has required methods/attributes
     - Class
   * - ``calls``
     - Function calls expected callees
     - Path/module (advanced)
   * - ``has_import``
     - Objects imported from correct modules
     - Path/module (experimental)


Value Assertions
================

equal_value
-----------

.. code-block:: python

   equal_value(case, outputs, *vars, **kwargs)

Tests for exact equality between expected and actual outputs.

**Positional outputs** (functions): compares return values element-by-element; missing or extra
outputs fail.

**Named outputs** (code strings): pass variable names as ``*vars`` to compare specific variables.
A variable the submission did not define fails the assertion.

Values are compared with ``==``; numpy arrays are equal if they have the same shape and
elements. Note that ``nan != nan``: use ``almost_equal`` for results that may be NaN.

.. code-block:: python

   # Function: compare return value
   assertions = {equal_value: ((), {})}

   # Code string: compare variables a and b
   assertions = {equal_value: (("a", "b"), {})}


almost_equal
------------

.. code-block:: python

   almost_equal(case, outputs, *vars, atol=1e-7, rtol=1e-7, **kwargs)

Tests for approximate equality using ``numpy.testing.assert_allclose``.
Actual and expected values must have the same shape (no broadcasting: ``0.0`` does not match
``np.zeros(3)``). Falls back to exact equality for non-numeric types.

**Parameters:**

- ``*vars``: variable names to compare (for named outputs)
- ``atol``: absolute tolerance (default ``1e-7``)
- ``rtol``: relative tolerance (default ``1e-7``)

.. code-block:: python

   # Function returning floats
   assertions = {almost_equal: ((), {"atol": 1e-6, "rtol": 1e-6})}

   # Code string: check variable "result" with tolerance
   assertions = {almost_equal: (("result",), {"atol": 1e-4})}


equal_contents
--------------

.. code-block:: python

   equal_contents(case, outputs, *vars, **kwargs)

Compares container contents with type coercion — an actual container is cast to the
expected container type (``list``, ``tuple``, ``set``, ``frozenset``, ``dict``) before
comparison. Useful when students might return a ``list`` where a ``tuple`` was expected.
Scalars are compared without any cast, and missing or extra outputs fail.

.. code-block:: python

   assertions = {equal_contents: (("my_list",), {})}


Scope Assertions
================

equal_scope
-----------

.. code-block:: python

   equal_scope(case, outputs, *args, **kwargs)

Tests that the set of variable names in the output scope matches the expected scope exactly.
No extra arguments needed.

.. code-block:: python

   assertions = {equal_scope: ((), {})}


equal_types
-----------

.. code-block:: python

   equal_types(case, outputs, *vars, **kwargs)

Tests that the named variables are instances of the types of the expected values
(an ``isinstance`` check: ``True`` passes where an ``int`` is expected, but not vice versa).

.. code-block:: python

   assertions = {equal_types: (("a", "b"), {})}


Exception Assertions
====================

raises
------

.. code-block:: python

   raises(case, outputs, *exception_types, **kwargs)

When ``TestCase.raises=True``, the harness catches the exception raised by the submission and
passes it as ``outputs``. This assertion verifies the exception is an instance of one of the
given types; if the submission does not raise, it fails. The built-in assertions that compare
outputs are not applied to the exception, so ``raises=True`` cases can share a subtask with
ordinary cases. ``file_contents``, which checks files on disk, still runs for ``raises=True``
cases, and so do custom assertions, which receive the exception as ``outputs`` unless they set
``accepts_exceptions = False``.

.. code-block:: python

   case = TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True)
   assertions = {raises: ((ZeroDivisionError,), {})}


File Assertions
===============

file_contents
-------------

.. code-block:: python

   file_contents(case, outputs, *args, **kwargs)

Compares the contents of files listed in ``case.expected[1]`` (a dict mapping filenames to
expected bytes) against the actual file contents on disk. The comparison is byte-for-byte;
a missing file fails.

.. code-block:: python

   case = TestCase(
       inputs=((), {}),
       expected=((), {"output.txt": b"Hello, World!\n"}),
   )
   assertions = {file_contents: ((), {})}


Timing Assertions
=================

time_bounds
-----------

.. code-block:: python

   time_bounds(case, outputs, *args, **kwargs)

Tests that the execution time (``outputs[2]``) falls within ``case.timing`` bounds (inclusive).
The timing tuple is ``(lower_bound, upper_bound)`` in seconds; use ``None`` for unbounded.
The time is measured after the call returns; long-running code is not interrupted.

.. code-block:: python

   case = TestCase(
       inputs=((large_input,), {}),
       expected=((result,), {}),
       timing=(None, 2.0),  # must finish within 2 seconds
   )
   assertions = {time_bounds: ((), {})}


Object Assertions
=================

equal_attributes
----------------

.. code-block:: python

   equal_attributes(case, outputs, *attrs, **kwargs)

Compares attribute values between expected and actual class instances.
Each object in ``outputs[0]`` (one per instantiation) is compared with the corresponding
object in ``case.expected[0]`` (a tuple or list); a different number of objects, or an
attribute missing on the actual object, fails.

.. code-block:: python

   assertions = {equal_attributes: (("x", "y"), {})}


close_attributes
----------------

.. code-block:: python

   close_attributes(case, outputs, *attrs, **kwargs)

Like ``equal_attributes`` but uses ``numpy.testing.assert_allclose`` for comparison.
Accepts ``atol`` and ``rtol`` keyword arguments. Custom harnesses may pass a bare instance
as ``outputs``.

.. code-block:: python

   assertions = {close_attributes: (("x", "y"), {"atol": 1e-6, "rtol": 1e-6})}


has_method
----------

.. code-block:: python

   has_method(case, outputs, *method_names, **type_hints)

Tests that the return object has the specified methods or attributes.
Optional ``**type_hints`` map attribute names to expected types.

.. code-block:: python

   assertions = {has_method: (("__repr__", "__add__"), {"x": float, "y": float})}


Advanced Assertions
===================

calls
-----

.. code-block:: python

   calls(case, outputs, caller, **callees)

Tests that calling ``caller`` on the return object triggers the expected calls to ``callees``.
Uses ``unittest.mock.patch.object`` internally.

.. code-block:: python

   assertions = {calls: (("main",), {"helper": [((1, 2), {})]})}

This verifies that calling ``obj.main()`` causes ``obj.helper(1, 2)`` to be called.


has_import
----------

.. code-block:: python

   has_import(case, outputs, *module_paths, **objects)

.. warning::

   ``has_import`` is experimental. Locations are compared as paths relative to the directory
   pytest runs in, so it only works for modules located there, not for the standard library
   or installed packages.

Tests whether objects in a module were imported from the correct locations. Each positional
``pathlib.Path`` requires ``import <stem>`` of that file; each keyword maps a name defined in
the module to the path it must be imported from, or ``None`` if it must be defined locally.

.. code-block:: python

   # student module: "import helpers" and "from helpers import area", defines "main" itself
   assertions = {has_import: ((Path("helpers.py"),), {"area": Path("helpers.py"), "main": None})}
