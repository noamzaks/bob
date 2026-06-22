from pathlib import Path
from typing import Literal, overload

from bob.api.rule import Rule, RuleInput
from bob.api.scope import AttributeScope, Scope
from bob.api.variable import Variable


class ScopedValue[T]:
    def __init__(self, value: None | T = None) -> None:
        self.value = value

    @overload
    def get(
        self, required: Literal[False] = False, default: None = None
    ) -> None | T: ...

    @overload
    def get(self, required: Literal[False] = False, default: T = ...) -> T: ...

    @overload
    def get(self, required: Literal[True] = True, default: None | str = None) -> T: ...

    def get(self, required=True, default: None | T = None):
        if self.value is None:
            if required:
                raise ValueError("Required non-present value!")

            return default

        return self.value

    def set(self, value: T) -> Scope:
        return AttributeScope(self, {"value": value})

    def add(self, value: T) -> Scope:
        return self.set(self.get() + value)  # ty:ignore[unsupported-operator]


class ScopedRule[OutputType](ScopedValue[Rule[OutputType]]):
    def __init__(self, base: Rule[OutputType]) -> None:
        super().__init__(base)

        self.single_input = base.single_input
        self.single_output = base.single_output
        self.variable_names = base.variable_names
        self.variables: dict[str, RuleInput.Multiple] = {}

    def set(self, value: Rule[OutputType]) -> Scope:
        if value.single_input != self.single_input:
            raise ValueError(
                "Invalid rule provided: expected a rule which accepts a single input!"
            )
        if value.single_output != self.single_output:
            raise ValueError(
                "Invalid rule provided: expected a rule which accepts a single input!"
            )

        return super().set(value)

    def build(
        self,
        *outputs: str | Path,
        inputs: None | list[RuleInput.Type] = None,
        implicit: None | list[RuleInput.Type] = None,
        order_only: None | list[RuleInput.Type] = None,
        implicit_outputs: None | list[str | Path] = None,
        pool: None | str = None,
        dyndep: None | str = None,
        variables: None | dict[str, RuleInput.Multiple] = None,
    ):
        assert self.value is not None

        if variables is None:
            variables = {}

        for key, value in self.variables.items():
            if key in self.value.variable_names:
                variables[key] = value

        return self.value.build(
            *outputs,
            inputs=inputs,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
            pool=pool,
            dyndep=dyndep,
            variables=variables,
        )

    def __getitem__(self, name: str) -> Variable:
        return Variable(name, self)
