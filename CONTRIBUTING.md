# Contributing
## Tooling
- `flit` for building and distribution
- `pyflakes` for linting
- `pyright` for type checking
- `black` for formatting
- `isort` for import sorting
- `pdoc` for generating documentation

## Tests
Tests are implemented using [`pytest`](https://docs.pytest.org/en/7.1.x/) and you run them with the command `pytest` while being in the root directory.

## Logging
Logging is implemented using [`logging`](https://docs.python.org/3/library/logging.html). To get logging messages of a specific level, initialize logging in the implementing code with the following lines:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

To run asyncio in [debug mode](https://docs.python.org/3/library/asyncio-dev.html#debug-mode), set the environment variable `PYTHONDEVMODE` or `PYTHONASYNCIODEBUG` to 1.

## Docstrings
Docstrings is used to document code according to the following template:

```python
"""Module summary

More in-depth information of the module. This docstring is placed at the top of the file, over the imports.
"""
import asyncio

def my_function(arg_1: str, arg_2: int) -> int:
    """Summary of my_function.

    Takes in a name and number.

    Returns a pair of glasses.
    """
    pass


class MyClass:
    """Summary of MyClass, max 80 characters long.

    Some more in-depth information about MyClass.
    """

    variable_1: str
    """The first variable"""

    variable_2: int
    """The second variable"""

    def __init__(arg_1: str) -> None:
        """Initializes object, where arg_1 is your `variable_1`."""
        self.variable_1 = arg_1

    def my_method(arg_1: str, arg_2: int) -> int:
        """Summary of my_simple_method.

        Takes in a name and number.

        Returns something nice.
        """
        pass
```
