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


def test_build_always(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            Rule("echo hi > $out", always=True).build("hi")
    """)
    )

    build(builddir, bobfile)
    assert (builddir / "hi").read_text() == "hi\n"

    with (
        assert_modification_time_increases(builddir / "hi"),
    ):
        build(builddir, bobfile)
        assert (builddir / "hi").read_text() == "hi\n"


def test_build_shell_output_rule(
    unique_tmp_path: Path, bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            built_magic = shell_output_rule("cat magic").build("magic")
            Rule("cp $in $out").build("copied_magic", inputs=[built_magic])
    """)
    )

    magic_path = unique_tmp_path / "magic"
    magic_path.write_text("initial magic")

    built_magic_path = builddir / "magic"
    copied_magic_path = builddir / "copied_magic"

    build(builddir, bobfile)
    assert (
        built_magic_path.read_text() == copied_magic_path.read_text() == "initial magic"
    )

    with (
        assert_modification_time_does_not_change(built_magic_path),
        assert_modification_time_does_not_change(copied_magic_path),
    ):
        build(builddir, bobfile)
        assert (
            built_magic_path.read_text()
            == copied_magic_path.read_text()
            == "initial magic"
        )

    magic_path.write_text("modified magic")

    with (
        assert_modification_time_increases(built_magic_path),
        assert_modification_time_increases(copied_magic_path),
    ):
        build(builddir, bobfile)
        assert (
            built_magic_path.read_text()
            == copied_magic_path.read_text()
            == "modified magic"
        )


def test_build_shell(unique_tmp_path: Path, bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            output = shell("cat magic")
            Rule(f"echo {output} > $out").build("magic")
    """)
    )

    magic_path = unique_tmp_path / "magic"
    magic_path.write_text("initial magic")

    built_magic_path = builddir / "magic"

    build(builddir, bobfile)
    assert built_magic_path.read_text() == "initial magic\n"

    with (
        assert_modification_time_does_not_change(built_magic_path),
        assert_modification_time_does_not_change(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)
        assert built_magic_path.read_text() == "initial magic\n"

    magic_path.write_text("modified magic")

    with (
        assert_modification_time_increases(built_magic_path),
        assert_modification_time_increases(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)
        assert built_magic_path.read_text() == "modified magic\n"
