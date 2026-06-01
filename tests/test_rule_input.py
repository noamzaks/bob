"""Pure-function tests for `BuildInput.add`. The resolver needs an active
`BobContext`; its semantics are exercised via Bobfiles in `test_rule.py`."""

from pathlib import Path

from bob.core.rule import BuildInput
from bob.core.targets import FileTarget, PhonyTarget, RootRelativePath


def test_add_strips_none():
    assert BuildInput.add(None, "x", None, "y") == ["x", "y"]


def test_add_flattens_lists():
    assert BuildInput.add(["a", "b"], "c", ["d"]) == ["a", "b", "c", "d"]


def test_add_passes_paths_and_targets_through_without_wrapping():
    p = Path("p.c")
    rp = RootRelativePath("rp.c")
    ph = PhonyTarget("all")
    ft = FileTarget(RootRelativePath("out.o"))
    result = BuildInput.add(p, rp, ph, ft)
    # No normalization — the helper must preserve each element's runtime class
    # so downstream resolvers can branch on it.
    assert isinstance(result[0], Path) and not isinstance(result[0], RootRelativePath)
    assert isinstance(result[1], RootRelativePath)
    assert isinstance(result[2], PhonyTarget)
    assert isinstance(result[3], FileTarget)
    assert result == [p, rp, ph, ft]


def test_add_empty_returns_empty_list():
    assert BuildInput.add() == []
    assert BuildInput.add(None, None) == []


def test_add_single_list_preserves_order():
    assert BuildInput.add(["a", "b", "c"]) == ["a", "b", "c"]
