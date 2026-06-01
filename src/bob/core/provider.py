import copy
from typing import Dict, Generic, List, Literal, Optional, TypeVar, overload

from bob.core import BuildInput, OutputType
from bob.core.context import BobContext
from bob.core.rule import Rule
from bob.core.scope import AttributeScope, Scope
from bob.core.variable import Variable

T = TypeVar("T")


class Provider(Generic[T]):
    def __init__(self, value: Optional[T] = None):
        context = BobContext.get()
        context.providers.append(self)

        self.value = value
        self._backups: List[Optional[T]] = []

    @overload
    def get(
        self, optional: Literal[False] = False, default: Optional[T] = None
    ) -> T: ...

    @overload
    def get(
        self, optional: Literal[True] = True, default: Optional[T] = None
    ) -> Optional[T]: ...

    def get(self, optional=False, default: Optional[T] = None) -> Optional[T]:
        """Get the current value of the provider."""

        if optional and self.value is None:
            return default

        return self.value

    def provide(self, value: T) -> Scope:
        """Return a scope where the given value is provided."""

        return AttributeScope(self, {"value": value})

    def extend(self, value: T) -> Scope:
        """Return a scope where the given value is added to the current one."""

        current = self.get()
        assert current is not None
        return self.provide(current + value)  # ty:ignore[unsupported-operator]

    def _backup(self):
        self._backups.append(self.value)

    def _restore(self):
        self.value = self._backups.pop()


class RuleProvider(Generic[OutputType], Provider[Rule[OutputType]]):
    def __init__(
        self,
        base: Rule[OutputType],
    ):
        super().__init__(base)
        self.single_input = base.single_input
        self.single_output = base.single_output
        self.variables = base.variables

        self._backups: List[Dict[str, BuildInput.Type]] = []
        self.values: Dict[str, BuildInput.Type] = {}

        base.provider = self

    def provide(self, value: Rule[OutputType]) -> Scope:
        """
        Return a scope where the given rule is provided.
        """

        if self.single_input is not None and self.single_input != value.single_input:
            raise ValueError(
                f"Cannot provide non-compatible rule: expected single_input={self.single_input} but got {value.single_input}!"
            )
        if self.single_output is not None and self.single_output != value.single_output:
            raise ValueError(
                f"Cannot provide non-compatible rule: expected single_output={self.single_output} but got {value.single_output}!"
            )

        return super().provide(value) | AttributeScope(value, {"provider": self})

    def __getitem__(self, variable: str) -> Variable:
        return Variable(self, name=variable)

    def _backup(self):
        self._backups.append(copy.deepcopy(self.values))

    def _restore(self):
        self.values = self._backups.pop()
