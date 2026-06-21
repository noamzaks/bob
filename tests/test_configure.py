from pathlib import Path
from textwrap import dedent

import pytest
from utilities import ROOT, assert_modification_time_does_not_change

from bob.commands.configure import configure
from bob.constants import get_build_ninja_path

CASES_PATH = ROOT / "tests" / "cases"


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
