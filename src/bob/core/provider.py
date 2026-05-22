from typing import Generic, List, Optional, TypeVar

from bob.core.context import BobContext
from bob.core.rule import Rule
from bob.core.scope import AttributeScope

T = TypeVar("T")


class Provider(Generic[T]):
    def __init__(self, value: Optional[T] = None):
        context = BobContext.get()
        context.providers.append(self)

        self.value = value
        self._backups: List[Optional[T]] = []

    def get(self, optional=False, default=None):
        if optional and self.value is None:
            return default

        return self.value

    def provide(self, value: T):
        return AttributeScope(self, {"value": value})

    def _backup(self):
        self._backups.append(self.value)

    def _restore(self):
        self.value = self._backups.pop()


class RuleProvider(Provider[Rule]):
    def __init__(
        self,
        value: Optional[Rule] = None,
        single_input: Optional[bool] = None,
        single_output: Optional[bool] = None,
    ):
        super().__init__(value)

        if value is not None:
            if single_input is not None or single_output is not None:
                raise ValueError(
                    "RuleProvider takes single_input/single_output from rule when provided!"
                )
            single_input = value.single_input
            single_output = value.single_output

        self.single_input = single_input
        self.single_output = single_output

    def provide(self, value):
        if self.single_input is not None and self.single_input != value.single_input:
            raise ValueError(
                f"Cannot provide non-compatible rule: expected single_input={self.single_input} but got {value.single_input}!"
            )
        if self.single_output is not None and self.single_output != value.single_output:
            raise ValueError(
                f"Cannot provide non-compatible rule: expected single_output={self.single_output} but got {value.single_output}!"
            )

        return super().provide(value)

    def build(self, *args, **kwargs):
        return self.get().build(*args, **kwargs)

    __call__ = build
