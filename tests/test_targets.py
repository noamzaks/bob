"""Pure-function tests for `bob.core.targets`."""

import dataclasses
from pathlib import Path

import pytest

from bob.core.targets import FileTarget, PhonyTarget, RootRelativePath


def test_root_relative_path_str_round_trip():
    p = RootRelativePath("foo/bar")
    assert str(p) == "foo/bar"
    assert p.value == Path("foo/bar")


def test_root_relative_path_accepts_path_and_rrp():
    direct = RootRelativePath(Path("a/b"))
    nested = RootRelativePath(direct)
    assert direct.value == nested.value == Path("a/b")


def test_truediv_appends_segment():
    assert (RootRelativePath("a") / "b").value == Path("a/b")


def test_parent_returns_one_level_up():
    assert RootRelativePath("a/b/c").parent.value == Path("a/b")


def test_parent_at_root_raises():
    with pytest.raises(ValueError, match="escaping"):
        RootRelativePath(".").parent


def test_with_suffix_returns_new_rrp():
    p = RootRelativePath("x.c").with_suffix(".o")
    assert isinstance(p, RootRelativePath)
    assert p.value == Path("x.o")


def test_phony_target_is_frozen_dataclass():
    a = PhonyTarget("all")
    assert a.name == "all"
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.name = "other"  # ty:ignore[invalid-assignment]


def test_phony_target_hashable_and_compares_by_name():
    assert PhonyTarget("x") == PhonyTarget("x")
    assert PhonyTarget("x") != PhonyTarget("y")
    assert len({PhonyTarget("x"), PhonyTarget("x")}) == 1


def test_file_target_wraps_rrp():
    ft = FileTarget(RootRelativePath("out.txt"))
    assert ft.path.value == Path("out.txt")


def test_root_relative_path_no_anchor_when_use_current_source_dir_false():
    # With no BobContext and use_current_source_dir=False, the path is taken
    # verbatim (anchored at ".") rather than against a current source dir.
    assert RootRelativePath("a/b", use_current_source_dir=False).value == Path("a/b")


def test_root_relative_path_curdir_param_overrides_context():
    # An explicit curdir takes precedence over any context-derived anchor.
    p = RootRelativePath("x.txt", curdir=RootRelativePath("base/dir"))
    assert p.value == Path("base/dir/x.txt")
