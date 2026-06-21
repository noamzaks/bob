from pathlib import Path
from textwrap import dedent

from utilities import (
    assert_modification_time_does_not_change,
    assert_modification_time_increases,
)

from bob.commands.build import build
from bob.constants import get_build_ninja_path


def test_build_lazy_glob(unique_tmp_path: Path, bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            glob("**/*.c", "dummy")
    """)
    )

    for f in (
        unique_tmp_path / "dummy" / "inside" / "a.txt",
        unique_tmp_path / "another" / "fun.txt",
        unique_tmp_path / "outside.txt",
        unique_tmp_path / "dummy" / "a.c",
    ):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")

    build(builddir, bobfile)

    with (
        assert_modification_time_does_not_change(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)

    (unique_tmp_path / "dummy" / "inside" / "sheesh.c").write_bytes(b"")

    with (
        assert_modification_time_increases(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)
