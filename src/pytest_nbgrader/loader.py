"""
Interface module between ipynb and pytest

Exports:
  Submission -- interface class to hold one `submission`
"""

import functools
import importlib.machinery
import importlib.util
import inspect
import pathlib
import types


class Submission:
    """
    Store submission object from notebooks.

    Attributes
    ----------
      submission -- object to be written from notebook
    """

    submission = None

    @functools.singledispatchmethod
    @classmethod
    def submit(cls, submission):
        """General method, does nothing but store."""
        print(f"The following submission will be tested:\n\n{submission}")
        cls.submission = submission

    @submit.register
    @classmethod
    def _(cls, cell: str) -> types.CodeType:
        """Compile string to bytecode ready for execution."""
        print(f"The following submission will be tested:\n\n{cell}")
        cls.submission = compile(cell, "student solution", "exec")
        return cls.submission

    @submit.register
    @classmethod
    def _(cls, function: types.FunctionType) -> types.FunctionType:
        """Read a function from the user's scope to be tested."""
        print(f"The following submission will be tested:\n\n{inspect.getsource(function)}")
        cls.submission = function
        return cls.submission

    @submit.register
    @classmethod
    def _(cls, clss: type) -> type:
        """Read a class from the user's scope to be tested."""
        print(f"The class {clss} will be tested (source code not shown)")
        cls.submission = clss
        return cls.submission

    @submit.register
    @classmethod
    def _(cls, module: pathlib.Path) -> importlib.machinery.ModuleSpec:
        """Store module spec from passed file path"""
        with pathlib.Path(module).open() as file:
            print(f"The following module will be tested:\n\n{file.read()}")
        cls.submission = importlib.util.spec_from_file_location(module.stem, module.resolve())
        return cls.submission
