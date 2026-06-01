"""Pure-function tests for `bob.core.expression.Expression` and `Variable`."""

from pathlib import Path

import pytest

from bob.core.expression import Expression
from bob.core.variable import Variable


def test_expression_parse_literal_only():
    expr = Expression.parse("just text")
    assert expr.parts == ["just text"]
    assert expr.variables == set()


def test_expression_parse_extracts_dollar_refs():
    expr = Expression.parse("$cc -o $out $in")
    assert expr.variables == {"cc", "out", "in"}


def test_expression_parse_escapes_double_dollar():
    expr = Expression.parse("echo $$HOME > $out")
    assert "HOME" not in expr.variables
    assert "out" in expr.variables


def test_expression_parse_none_yields_empty():
    assert Expression.parse(None).parts == []


def test_expression_parse_from_path():
    assert Expression.parse(Path("foo/bar")).parts == ["foo/bar"]


def test_expression_join_emits_dollar_refs_by_default():
    assert Expression.parse("$a/$b.c").expand() == "$a/$b.c"


def test_expression_join_empty_returns_none():
    assert Expression.parse(None).expand() is None


def test_expression_join_substitutes_provided_values():
    assert Expression.parse("$x-$y").expand(x="A", y="B") == "A-B"


def test_expression_validate_accepts_known_variables():
    Expression.parse("$cc $cflags").validate({"cc": "clang", "cflags": ["-O2"]})


def test_expression_validate_passes_through_in_out_without_value():
    # `$in` / `$out` are Ninja built-ins; never need an explicit value.
    Expression.parse("cat $in > $out").validate({})


def test_expression_validate_raises_on_uninitialized():
    with pytest.raises(ValueError, match='"missing" is uninitialized'):
        Expression.parse("$missing").validate({})


def test_expression_validate_rejects_unused_variable():
    with pytest.raises(KeyError, match="Unused variable extra"):
        Expression.parse("$known").validate({"known": "x", "extra": "y"})


def test_expression_validate_allow_unused_accepts_extras():
    Expression.parse("$known").validate({"known": "x", "extra": "y"}, allow_unused=True)


def test_expression_validate_rejects_invalid_value_type():
    with pytest.raises(AssertionError, match="Invalid variable"):
        Expression.parse("$x").validate({"x": 123})


def test_variable_instances_in_parts():
    expr = Expression.parse("a$b")
    assert isinstance(expr.parts[1], Variable)
    assert expr.parts[1].name == "b"


def test_expression_parse_underscore_variable_name():
    expr = Expression.parse("$foo_bar")
    assert expr.variables == {"foo_bar"}


def test_expression_parse_two_adjacent_variables_split_into_separate_parts():
    expr = Expression.parse("$a$b")
    assert [str(p) for p in expr.parts] == ["a", "b"]
    assert expr.variables == {"a", "b"}


def test_expression_parse_brace_variable_syntax():
    expr = Expression.parse("${foo}")
    assert expr.variables == {"foo"}
    assert expr.expand() == "$foo"
