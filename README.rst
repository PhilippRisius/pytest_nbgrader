===============
pytest-nbgrader
===============

+----------------------------+-----------------------------------------------------+
| Versions                   | |pypi|                                              |
+----------------------------+-----------------------------------------------------+
| Documentation and Support  | |docs| |versions|                                   |
+----------------------------+-----------------------------------------------------+
| Open Source                | |license| |ossf-score|                              |
+----------------------------+-----------------------------------------------------+
| Coding Standards           | |ruff| |pre-commit|                                 |
+----------------------------+-----------------------------------------------------+
| Development Status         | |status| |build| |coveralls|                        |
+----------------------------+-----------------------------------------------------+

Pytest plugin for using with nbgrader and generating test cases.

* Free software: MIT license
* Documentation: https://pytest-nbgrader.readthedocs.io.

Features
--------

* Load student submissions from Jupyter notebooks via ``Submission`` class
* Define test cases with expected inputs/outputs using ``TestCase`` and ``TestSubtask`` dataclasses
* Execute student code against test cases with automatic result comparison
* Serialize and deserialize test cases via YAML
* Prerequisite checks: function signature validation, write-access verification
* Assertion helpers for numeric comparisons (numpy-based tolerances)
* Automatic pytest test class generation via ``TestClass`` harness
* Run pytest from within notebooks using the ``runner`` module
* Plugs into pytest as a standard plugin — no configuration needed beyond install

Credits
-------

This package was created with Cookiecutter_ and the `Ouranosinc/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/cookiecutter/cookiecutter
.. _`Ouranosinc/cookiecutter-pypackage`: https://github.com/Ouranosinc/cookiecutter-pypackage

.. |build| image:: https://github.com/PhilippRisius/pytest_nbgrader/actions/workflows/main.yml/badge.svg
        :target: https://github.com/PhilippRisius/pytest_nbgrader/actions
        :alt: Build Status

.. |coveralls| image:: https://coveralls.io/repos/github/PhilippRisius/pytest_nbgrader/badge.svg
        :target: https://coveralls.io/github/PhilippRisius/pytest_nbgrader
        :alt: Coveralls

.. |docs| image:: https://readthedocs.org/projects/pytest-nbgrader/badge/?version=latest
        :target: https://pytest-nbgrader.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

.. |license| image:: https://img.shields.io/github/license/PhilippRisius/pytest_nbgrader.svg
        :target: https://github.com/PhilippRisius/pytest_nbgrader/blob/main/LICENSE
        :alt: License

..
    .. |ossf-bp| image:: https://bestpractices.coreinfrastructure.org/projects/9945/badge
            :target: https://bestpractices.coreinfrastructure.org/projects/9945
            :alt: Open Source Security Foundation Best Practices

.. |ossf-score| image:: https://api.securityscorecards.dev/projects/github.com/PhilippRisius/pytest_nbgrader/badge
        :target: https://securityscorecards.dev/viewer/?uri=github.com/PhilippRisius/pytest_nbgrader
        :alt: OpenSSF Scorecard

.. |pre-commit| image:: https://results.pre-commit.ci/badge/github/PhilippRisius/pytest_nbgrader/main.svg
        :target: https://results.pre-commit.ci/latest/github/PhilippRisius/pytest_nbgrader/main
        :alt: pre-commit.ci status

.. |pypi| image:: https://img.shields.io/pypi/v/pytest-nbgrader.svg
        :target: https://pypi.org/project/pytest-nbgrader/
        :alt: PyPI

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
        :target: https://github.com/astral-sh/ruff
        :alt: Ruff

.. |status| image:: https://www.repostatus.org/badges/latest/active.svg
        :target: https://www.repostatus.org/#active
        :alt: Project Status: Active – The project has reached a stable, usable state and is being actively developed.

.. |versions| image:: https://img.shields.io/pypi/pyversions/pytest-nbgrader.svg
        :target: https://pypi.org/project/pytest-nbgrader/
        :alt: Supported Python Versions
