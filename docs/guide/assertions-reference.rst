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

**Positional outputs** (functions): compares return values element-by-element.

**Named outputs** (code strings): pass variable names as ``*vars`` to compare specific variables.

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
Falls back to exact equality for non-numeric types.

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

Compares container contents with type coercion — the actual output is cast to the
expected type before comparison. Useful when students might return a ``list`` where a
``tuple`` was expected.

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

Tests that the types of named variables match between expected and actual outputs.

.. code-block:: python

   assertions = {equal_types: (("a", "b"), {})}


Exception Assertions
====================

raises
------

.. code-block:: python

   raises(case, outputs, *exception_types, **kwargs)

When ``TestCase.raises=True``, the harness catches the exception and passes it as ``outputs``.
This assertion verifies the exception is an instance of one of the given types.

.. code-block:: python

   case = TestCase(inputs=((1, 0), {}), expected=((), {}), raises=True)
   assertions = {raises: ((ZeroDivisionError,), {})}


File Assertions
===============

file_contents
-------------

.. code-block:: python

   file_contents(case, *args, **kwargs)

Compares the contents of files listed in ``case.expected[1]`` (a dict mapping filenames to
expected bytes) against the actual file contents on disk. The comparison is byte-for-byte.

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

Tests that the execution time (``outputs[2]``) falls within ``case.timing`` bounds.
The timing tuple is ``(lower_bound, upper_bound)`` in seconds; use ``None`` for unbounded.

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
The expected instance comes from ``case.expected[0][0]``, the actual from ``outputs[0][0]``.

.. code-block:: python

   assertions = {equal_attributes: (("x", "y"), {})}


close_attributes
----------------

.. code-block:: python

   close_attributes(case, outputs, *attrs, **kwargs)

Like ``equal_attributes`` but uses ``numpy.testing.assert_allclose`` for comparison.
Accepts ``atol`` and ``rtol`` keyword arguments.

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

.. warning::

   ``has_import`` is experimental and has known compatibility issues.
   It uses ``case.return_object`` (a dynamic attribute not declared on ``TestCase``)
   and is not wrapped with the standard ``@_log`` decorator pipeline.
   Use with caution.

Tests whether objects in a module were imported from the correct locations.
