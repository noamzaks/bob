"""Pure-function tests for `bob.core.scope` and `bob.core.rule.flatten`."""

import pytest

from bob.core.scope import AttributeScope, DictionaryScope, ScopeList


def test_dictionary_scope_overlays_and_restores():
    d = {"a": 1}
    with DictionaryScope(d, {"a": 2, "b": 3}):
        assert d == {"a": 2, "b": 3}
    assert d == {"a": 1}


def test_dictionary_scope_close_rejects_external_mutation():
    d = {"k": "orig"}
    scope = DictionaryScope(d, {"k": "new"})
    d["k"] = "tampered"
    with pytest.raises(AssertionError):
        scope.close()


class _Obj:
    a = 1


def test_attribute_scope_overlays_and_restores():
    obj = _Obj()
    with AttributeScope(obj, {"a": 9, "b": "added"}):
        assert obj.a == 9 and obj.b == "added"  # ty:ignore[unresolved-attribute]
    assert obj.a == 1 and not hasattr(obj, "b")


def test_scope_list_or_chains_via_scope_list_lhs():
    d = {}
    s1 = DictionaryScope(d, {"a": 1})
    s2 = DictionaryScope(d, {"b": 2})
    s3 = DictionaryScope(d, {"c": 3})
    # `ScopeList | Scope` is the supported composition path; the plugin uses
    # it via Variable.provide(...) which already returns a ScopeList.
    with ScopeList([s1]) | s2 | s3:
        assert d == {"a": 1, "b": 2, "c": 3}
    assert d == {}


def test_two_bare_scopes_compose_via_or():
    d = {}
    with DictionaryScope(d, {"a": 1}) | DictionaryScope(d, {"b": 2}):
        assert d == {"a": 1, "b": 2}
    assert d == {}


def test_scope_list_constructor_accepts_list():
    d = {}
    composed = ScopeList([DictionaryScope(d, {"a": 1}), DictionaryScope(d, {"b": 2})])
    assert d == {"a": 1, "b": 2}
    composed.close()
    assert d == {}
