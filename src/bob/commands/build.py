import os
import subprocess
from pathlib import Path

from bob.commands.clean import clean
from bob.commands.compdb import compdb
from bob.constants import get_build_ninja_path
from bob.core.context import Context


def run_ninja(builddir: Path) -> None:
    arguments = [
        "ninja",
        "-f",
        str(get_build_ninja_path(builddir)),
    ]

    os.execvp(arguments[0], arguments)


def build(
    builddir: Path, bobfile: Path, do_clean: bool, no_compdb: bool, symlink_compdb: bool
) -> None:
    if do_clean:
        clean(builddir)

    with Context(builddir) as context:
        context.evaluate(bobfile)

    p: subprocess.Popen | None
    if not no_compdb:
        p = compdb(builddir, bobfile, dont_symlink=not symlink_compdb, wait=False)

    run_ninja(builddir)

    if p is not None:
        assert p.wait() == 0
