import re
from pathlib import Path
from typing import Any, Dict, List, Union

from bob.core.targets import FileTarget, RootRelativePath
from bob.core.variable import Variable


class Expression:
    """A list comprised of constant strings and variables."""

    VARIABLE_REGEX = re.compile(r"[a-zA-Z0-9]+")

    def __init__(self, parts: List[Union[str, Variable]]):
        self.parts = parts

    @property
    def variables(self):
        return {p.name for p in self.parts if isinstance(p, Variable)}

    @staticmethod
    def parse(expression: Union[None, str, Path]):
        """Return an expression represented by the given string or path."""

        if expression is None:
            return Expression([])

        if isinstance(expression, Path):
            return Expression([str(expression)])

        parts: List[Union[str, Variable]] = []
        current = 0
        while current < len(expression):
            try:
                next = expression.index("$", current)
            except ValueError:
                if len(parts) != 0 and isinstance(parts[-1], str):
                    parts[-1] += expression[current:]
                else:
                    parts.append(expression[current:])

                break

            assert next + 1 < len(expression)
            if expression[next + 1] == "$":
                if len(parts) == 0:
                    parts.append("")

                parts[-1] += expression[current:next] + "$"
                current = next + 2
                continue

            match = Expression.VARIABLE_REGEX.search(expression, next + 1)
            assert match is not None

            if current != next:
                if len(parts) == 0 or isinstance(parts[-1], Variable):
                    parts.append("")

                parts[-1] += expression[current:next]

            name = match.group()
            parts.append(Variable(name=name))
            current = next + 1 + len(name)

        return Expression(parts)

    def expand(self, **values: str):
        """Encode the expression as a Ninja string, with the given variable values expanded."""

        if len(self.parts) == 0:
            return None

        output = ""

        for p in self.parts:
            if isinstance(p, Variable) and p.name in values:
                p = values[p.name]

            if isinstance(p, Variable):
                output += "$" + p.name
            else:
                output += p.replace("$", "$$")

        return output

    def validate(self, variables: Dict[str, Any], allow_unused=False):
        """
        Make sure all of the expression's variables are initialized and have a valid value, and if `allow_unused` is not set, there are no unused variables.
        """

        valid_variables = self.variables

        for key, value in variables.items():
            if value is None:
                continue

            if not isinstance(value, list):
                value = [value]

            assert isinstance(value, list) and all(
                isinstance(x, str)
                or isinstance(x, Path)
                or isinstance(x, RootRelativePath)
                or isinstance(x, FileTarget)
                for x in value
            ), f"Invalid variable {key} with value {value}"

            if not allow_unused and key not in valid_variables:
                raise KeyError(f"Unused variable {key}")

        for p in self.parts:
            if not isinstance(p, Variable):
                continue

            if p.name in variables and variables[p.name] is not None:
                continue

            if p.name == "in" or p.name == "out":
                continue

            raise ValueError(f'Variable "{p.name}" is uninitialized')
