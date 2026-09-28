"""
Interface module between ipynb and pytest.

Exports:
  Submission -- interface class to hold one `submission`
"""

from __future__ import annotations


__all__ = ["Submission"]

import collections.abc
import functools
import importlib.machinery
import importlib.util
import inspect
import pathlib
import types


class Submission:
    """Store submission object from notebooks."""

    #: The stored submission object.
    submission: object = None

    @functools.singledispatchmethod
    @classmethod
    def submit(cls, submission: object) -> object:
        """
        Store a generic submission.

        Parameters
        ----------
        submission : object
            The submission object to store.

        Returns
        -------
        object
            The stored submission.
        """
        print(f"The following submission will be tested:\n\n{submission}")
        cls.submission = submission
        return cls.submission

    @submit.register
    @classmethod
    def _(cls, cell: str) -> types.CodeType:
        """
        Compile string to bytecode ready for execution.

        Parameters
        ----------
        cell : str
            Source code string to compile.

        Returns
        -------
        types.CodeType
            Compiled bytecode.
        """
        # a failed submission must not leave the previous one in place
        cls.submission = None
        print(f"The following submission will be tested:\n\n{cell}")
        cls.submission = compile(cell, "student solution", "exec", dont_inherit=True)
        return cls.submission

    @submit.register(collections.abc.Callable)
    @submit.register(types.FunctionType)
    @classmethod
    def _(cls, function: collections.abc.Callable) -> collections.abc.Callable:
        """
        Read a function (or other non-class callable) from the user's scope to be tested.

        Parameters
        ----------
        function : callable
            The function to submit.

        Returns
        -------
        callable
            The stored function.
        """
        cls.submission = None
        try:
            source = inspect.getsource(inspect.unwrap(function))
        except (OSError, TypeError):
            source = repr(function)
        print(f"The following submission will be tested:\n\n{source}")
        cls.submission = function
        return cls.submission

    @submit.register
    @classmethod
    def _(cls, clss: type) -> type:
        """
        Read a class from the user's scope to be tested.

        Parameters
        ----------
        clss : type
            The class to submit.

        Returns
        -------
        type
            The stored class.
        """
        print(f"The class {clss} will be tested (source code not shown)")
        cls.submission = clss
        return cls.submission

    @submit.register
    @classmethod
    def _(cls, module: pathlib.Path) -> importlib.machinery.ModuleSpec:
        """
        Store module spec from passed file path.

        Parameters
        ----------
        module : pathlib.Path
            Path to the module file.

        Returns
        -------
        importlib.machinery.ModuleSpec
            The module specification.

        Raises
        ------
        ValueError
            If the file cannot be imported as a Python module.
        """
        cls.submission = None
        spec = importlib.util.spec_from_file_location(module.stem, module.resolve())
        if spec is None:
            raise ValueError(f"{module} cannot be imported as a Python module.")
        print(f"The following module will be tested:\n\n{module.read_text(encoding='utf-8')}")
        cls.submission = spec
        return cls.submission
