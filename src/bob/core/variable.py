import shlex
from typing import TYPE_CHECKING

from bob.core.scope import DictionaryScope, ScopeList

if TYPE_CHECKING:
    from bob.core.rule import Rule, RuleInput


class Variable:
    """An object representing a variable in some rules."""

    def __init__(self, *rules: "Rule", name: str):
        for rule in rules:
            if name not in rule.variables:
                raise KeyError(name)

        self.rules = rules
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Variable({repr(self.name)})"

    def provide(
        self,
        value: "RuleInput",
    ):
        """Return a scope with the variable set to `value` in each rule."""

        return ScopeList(
            [DictionaryScope(rule.values, {self.name: value}) for rule in self.rules]
        )

    def extend(self, value: "RuleInput"):
        """Return a scope with `value` added to the variable in each rule."""
        from bob.core.rule import rule_input_add

        return ScopeList(
            [
                DictionaryScope(
                    rule.values,
                    {self.name: rule_input_add(rule.values[self.name], value)},
                )
                for rule in self.rules
            ]
        )

    def get(self, optional=False, default=None):
        return (
            self.rules[0].values.get(self.name, default)
            if optional
            else self.rules[0].values[self.name]
        )

    def expand(self):
        value = self.get()
        return shlex.join(value) if isinstance(value, list) else shlex.quote(value)
