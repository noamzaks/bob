import os
import time
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Callable, Generator

import pytest
from utilities import ROOT

from bob.commands.configure import configure
from bob.constants import get_build_ninja_path
from bob.core.context import Context
from bob.prelude import Rule

CASES_PATH = ROOT / "tests" / "cases"


@pytest.fixture()
def builddir() -> Path:
    return Path("build")


@pytest.fixture()
def bobfile(tmp_path: Path) -> Path:
    return tmp_path / "Bobfile"


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path: Path) -> None:
    os.chdir(tmp_path)


@pytest.fixture()
def context(chdir_tmp, builddir: Path) -> Generator[Context, None, None]:
    with Context(builddir) as context:
        yield context


@pytest.mark.parametrize(
    "case", [case.stem for case in CASES_PATH.iterdir() if case.suffix == ".bob"]
)
def test_configure(pytestconfig: pytest.Config, case: str, builddir: Path) -> None:
    bobfile = (CASES_PATH / f"{case}.bob").resolve()
    expected_ninja_path = CASES_PATH / f"{case}.ninja"

    configure(builddir, bobfile)

    build_ninja_path = get_build_ninja_path(builddir)

    assert build_ninja_path.is_file()

    actual = build_ninja_path.read_text()
    actual = actual.replace(str(ROOT), "$root")

    if pytestconfig.getoption("--update"):
        expected_ninja_path.write_text(actual)
    else:
        expected = expected_ninja_path.read_text()
        assert actual == expected


def test_ninja_removed_when_configure_fails(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            Rule("echo hi > $out", description="ECHO").build("hi")
            raise Exception("configure exception")
    """)
    )

    with pytest.raises(Exception, match="configure exception"):
        configure(builddir, bobfile)

    assert not get_build_ninja_path(builddir).exists()


@contextmanager
def assert_modification_time_change(
    path: Path, checker: Callable[[float, float], bool]
) -> Generator[None, None, None]:
    before = path.stat().st_mtime

    # Make sure we give the filesystem the opportunity to change the mtime.
    time.sleep(0.1)

    yield

    after = path.stat().st_mtime
    assert checker(before, after)


@contextmanager
def assert_modification_time_does_not_change(path: Path) -> Generator[None, None, None]:
    with assert_modification_time_change(path, lambda before, after: before == after):
        yield


def test_configure_lazy(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            Rule("echo hi > $out", description="ECHO").build("hi")
    """)
    )

    configure(builddir, bobfile, lazy=True)
    assert get_build_ninja_path(builddir).is_file()

    with (
        assert_modification_time_does_not_change(get_build_ninja_path(builddir)),
    ):
        configure(builddir, bobfile, lazy=True)


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
