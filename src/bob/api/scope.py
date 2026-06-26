import abc
from types import TracebackType
from typing import Any, Self, Type

from bob.core.context import Context


class Scope(abc.ABC):
    def __init__(self) -> None:
        context = Context.current()
        if context.track_scopes:
            context.scopes.append(self)

    @abc.abstractmethod
    def _close(self) -> None: ...

    def __enter__(self) -> "Scope":
        return self

    def close(self) -> None:
        context = Context.current()
        if self not in context.scopes:
            return
        context.scopes.remove(self)
        self._close()

    def __exit__(
        self,
        exc_type: None | Type[BaseException],
        exc: None | BaseException,
        tb: None | TracebackType,
    ) -> None:
        self.close()

    def __or__(self, other: Self | "ScopeList") -> "Scope":
        return ScopeList([self]) | other


class ScopeList(Scope):
    def __init__(self, scopes: list[Scope]) -> None:
        super().__init__()
        self.scopes = scopes

    def _close(self) -> None:
        for scope in self.scopes:
            scope._close()

    def __or__(self, other: Scope | Self) -> Scope:
        if isinstance(other, ScopeList):
            return ScopeList(self.scopes + other.scopes)
        return ScopeList(self.scopes + [other])


class DictionaryScope(Scope):
    def __init__(self, variables: dict[str, Any], changes: dict[str, Any]) -> None:
        super().__init__()
        self.variables = variables
        self.changes = changes

        original: dict[str, Any] = {}
        for key, value in changes.items():
            if key in variables:
                original[key] = variables.pop(key)

            variables[key] = value

        self.original = original

    def _close(self) -> None:
        for key in self.changes:
            assert self.variables[key] == self.changes[key], (
                f"Expected {key} to be {self.changes[key]} when closing the scope but got: {self.variables[key]}"
            )

            if key in self.original:
                self.variables[key] = self.original[key]
            else:
                self.variables.pop(key)

        self.original = {}
        self.changes = {}
        self.variables = {}


class AttributeScope(Scope):
    def __init__(self, object: Any, changes: dict[str, Any]) -> None:
        super().__init__()
        self.object = object
        self.changes = changes

        original: dict[str, Any] = {}
        for key, value in changes.items():
            if hasattr(object, key):
                original[key] = getattr(object, key)

            setattr(object, key, value)

        self.original = original

    def _close(self) -> None:
        for key in self.changes:
            # The `object` mustn't have changed underneath our feet, we have no sensible action in that case.
            assert getattr(self.object, key) == self.changes[key], (
                f"Expected {key} to be {self.changes[key]} when closing the scope but got: {getattr(self.object, key)}"
            )

            if key in self.original:
                setattr(self.object, key, self.original[key])
            else:
                delattr(self.object, key)

        self.original = {}
        self.changes = {}
        self.object = None


def plugin_scope() -> Scope:
    context = Context.current()
    return AttributeScope(context, {"track_scopes": False})
