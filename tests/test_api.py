from pathlib import Path
from typing import Generator

import pytest

from bob.api.path import glob
from bob.api.rule import Rule
from bob.core.context import Context


@pytest.fixture()
def context(unique_tmp_path, builddir: Path) -> Generator[Context, None, None]:
    with Context(builddir) as context:
        yield context


def test_rule_unused_variable_in_constructor(context: Context) -> None:
    with pytest.raises(KeyError, match="dummy"):
        Rule("echo hi > $out", variables={"dummy": "hi"})


def test_rule_unused_variable_in_build(context: Context) -> None:
    rule = Rule("echo hi > $out")
    with pytest.raises(KeyError, match="dummy"):
        rule.build("hi", variables={"dummy": "hi"})


def test_rule_uninitialized_variable(context: Context) -> None:
    rule = Rule("echo $something > $out")
    with pytest.raises(ValueError, match='Variable "something" is uninitialized'):
        rule.build("hi")


def test_glob(unique_tmp_path: Path, context: Context) -> None:
    for f in (
        unique_tmp_path / "dummy" / "inside" / "a.txt",
        unique_tmp_path / "another" / "fun.txt",
        unique_tmp_path / "outside.txt",
        unique_tmp_path / "dummy" / "a.c",
    ):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")

    assert glob("**/*.txt", "dummy") == [Path("dummy/inside/a.txt")]
    assert glob("**/*.c") == [Path("dummy/a.c")]
