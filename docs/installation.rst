============
Installation
============

..
    We strongly recommend installing pytest nbgrader plugin in an Anaconda Python environment.
    Furthermore, due to the complexity of some packages, the default dependency solver can take a long time to resolve the environment.
    If `mamba` is not already your default solver, consider running the following commands in order to speed up the process:

        .. code-block:: console

            conda install -n base conda-libmamba-solver
            conda config --set solver libmamba

If you don't have `pip`_ installed, this `Python installation guide`_ can guide you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/

Stable release
--------------

To install pytest nbgrader plugin, run this command in your terminal:

.. code-block:: console

    python -m pip install pytest_nbgrader

..
    .. code-block:: console

        conda install pytest_nbgrader

This is the preferred method to install pytest nbgrader plugin, as it will always install the most recent stable release.


From sources
------------

The sources for pytest nbgrader plugin can be downloaded from the `Github repo`_.

#. Download the source code from the `Github repo`_ using one of the following methods:

    * Clone the public repository:

        .. code-block:: console

            git clone git@github.com:PhilippRisius/pytest_nbgrader_plugin.git

    * Download the `tarball <https://github.com/PhilippRisius/pytest_nbgrader/tarball/main>`_:

        .. code-block:: console

            curl -OJL https://github.com/PhilippRisius/pytest_nbgrader/tarball/main

#. Once you have a copy of the source, you can install it with:

    .. code-block:: console

        python -m pip install .

    ..
        .. code-block:: console

            conda env create -f environment-dev.yml
            conda activate pytest_nbgrader-dev
            make dev

        If you are on Windows, replace the ``make dev`` command with the following:

        .. code-block:: console

            python -m pip install -e .[dev]

        Even if you do not intend to contribute to `pytest nbgrader plugin`, we favor using `environment-dev.yml` over `environment.yml` because it includes additional packages that are used to run all the examples provided in the documentation.
        If for some reason you wish to install the `PyPI` version of `pytest nbgrader plugin` into an existing Anaconda environment (*not recommended if requirements are not met*), only run the last command above.

#. When new changes are made to the `Github repo`_, if using a clone, you can update your local copy using the following commands from the root of the repository:

    .. code-block:: console

        git fetch
        git checkout main
        git pull origin main
        python -m pip install .

    ..
        .. code-block:: console

            git fetch
            git checkout main
            git pull origin main
            conda env update -n pytest_nbgrader-dev -f environment-dev.yml
            conda activate pytest_nbgrader-dev
            make dev

    These commands should work most of the time, but if big changes are made to the repository, you might need to remove the environment and create it again.

.. _Github repo: https://github.com/PhilippRisius/pytest_nbgrader
