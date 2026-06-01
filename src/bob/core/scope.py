import abc
from typing import Any, Dict, List, Union


class Scope(abc.ABC):
    """
    A generic class that should perform certain changes when constructed and revert them when closed (or __exit__'ed).
    """

    @abc.abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> "Scope":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __or__(self, other: Union["Scope", "ScopeList"]) -> "Scope":
        return ScopeList([self]) | other


class ScopeList(Scope):
    """
    Create a scope from a list of scopes.
    """

    def __init__(self, scopes: List[Scope]) -> None:
        self.scopes = scopes

    def close(self) -> None:
        for scope in self.scopes:
            scope.close()

    def __or__(self, other: Union["Scope", "ScopeList"]) -> "Scope":
        if isinstance(other, ScopeList):
            return ScopeList(self.scopes + other.scopes)
        return ScopeList(self.scopes + [other])


class DictionaryScope(Scope):
    """
    Overlay given dictionary onto another dictionary.
    """

    def __init__(self, variables: Dict[str, Any], changes: Dict[str, Any]) -> None:
        self.variables = variables
        self.changes = changes

        original: Dict[str, Any] = {}
        for key, value in changes.items():
            if key in variables:
                original[key] = variables.pop(key)

            variables[key] = value

        self.original = original

    def close(self) -> None:
        for key in self.changes:
            # The `variables` mustn't have changed underneath our feet, we have no sensible action in that case.
            assert self.variables[key] == self.changes[key]

            if key in self.original:
                self.variables[key] = self.original[key]
            else:
                self.variables.pop(key)

        self.original = {}
        self.changes = {}
        self.variables = {}


class AttributeScope(Scope):
    """
    Overlay given attributes onto an object.
    """

    def __init__(self, object: Any, changes: Dict[str, Any]) -> None:
        self.object = object
        self.changes = changes

        original: Dict[str, Any] = {}
        for key, value in changes.items():
            if hasattr(object, key):
                original[key] = getattr(object, key)

            setattr(object, key, value)

        self.original = original

    def close(self) -> None:
        for key in self.changes:
            # The `object` mustn't have changed underneath our feet, we have no sensible action in that case.
            assert getattr(self.object, key) == self.changes[key]

            if key in self.original:
                setattr(self.object, key, self.original[key])
            else:
                delattr(self.object, key)

        self.original = {}
        self.changes = {}
        self.object = None
