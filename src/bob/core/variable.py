import shlex
from typing import TYPE_CHECKING, Union

from bob.core.scope import DictionaryScope, Scope, ScopeList

if TYPE_CHECKING:
    from bob.core.provider import RuleProvider
    from bob.core.rule import BuildInput, Rule


class Variable:
    """An object representing a variable in some rules or rule providers."""

    def __init__(self, *rules: "Union[Rule, RuleProvider]", name: str) -> None:
        for rule in rules:
            if name not in rule.variables:
                raise KeyError(name)

        self.rules = rules
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Variable({repr(self.name)})"

    def get(self, optional=False, default=None) -> "BuildInput.Type":
        return (
            self.rules[0].values.get(self.name, default)
            if optional
            else self.rules[0].values[self.name]
        )

    def provide(
        self,
        value: "BuildInput.Type",
    ) -> Scope:
        """Return a scope with the variable set to `value` in each rule."""

        return ScopeList(
            [DictionaryScope(rule.values, {self.name: value}) for rule in self.rules]
        )

    def extend(self, value: "BuildInput.Type") -> Scope:
        """Return a scope with `value` added to the variable in each rule."""
        from bob.core.rule import BuildInput

        return ScopeList(
            [
                DictionaryScope(
                    rule.values,
                    {self.name: BuildInput.add(rule.values[self.name], value)},
                )
                for rule in self.rules
            ]
        )

    def expand(self) -> str:
        value = self.get()
        if isinstance(value, list):
            return shlex.join(str(v) for v in value)
        return shlex.quote(str(value))
