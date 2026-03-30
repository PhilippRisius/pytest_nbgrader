============
Installation
============

If you don't have `pip`_ installed, this `Python installation guide`_ can guide you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/

Stable release
--------------

To install pytest-nbgrader, run this command in your terminal:

.. code-block:: console

    python -m pip install pytest_nbgrader

This is the preferred method to install pytest-nbgrader, as it will always install the most recent stable release.

The plugin registers automatically with pytest on install — no additional configuration
is needed. Any ``pytest`` invocation with the ``--cases`` flag will activate the plugin.

.. important::

   If you use nbgrader's ``autograde`` command on a server (e.g., JupyterHub), make sure
   pytest-nbgrader is installed in the **grading environment** as well, not just on the
   instructor's machine.

Optional extras
~~~~~~~~~~~~~~~

For development or building documentation locally:

.. code-block:: console

    python -m pip install pytest_nbgrader[dev]   # linting, testing, pre-commit
    python -m pip install pytest_nbgrader[docs]  # Sphinx and doc dependencies
    python -m pip install pytest_nbgrader[all]   # everything


From sources
------------

The sources for pytest-nbgrader can be downloaded from the `Github repo`_.

#. Download the source code from the `Github repo`_ using one of the following methods:

    * Clone the public repository:

        .. code-block:: console

            git clone git@github.com:PhilippRisius/pytest_nbgrader.git

    * Download the `tarball <https://github.com/PhilippRisius/pytest_nbgrader/tarball/main>`_:

        .. code-block:: console

            curl -OJL https://github.com/PhilippRisius/pytest_nbgrader/tarball/main

#. Once you have a copy of the source, you can install it with:

    .. code-block:: console

        python -m pip install .

#. When new changes are made to the `Github repo`_, if using a clone, you can update your local copy using the following commands from the root of the repository:

    .. code-block:: console

        git fetch
        git checkout main
        git pull origin main
        python -m pip install .

.. _Github repo: https://github.com/PhilippRisius/pytest_nbgrader

Next steps
----------

See the :doc:`usage` page for a quick start tutorial and guides for instructors and students.
