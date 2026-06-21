import subprocess
from pathlib import Path

from bob.commands.clean import clean
from bob.commands.compdb import compdb
from bob.commands.configure import configure
from bob.constants import get_build_ninja_path


def run_ninja(builddir: Path) -> None:
    arguments = [
        "ninja",
        "-f",
        str(get_build_ninja_path(builddir)),
    ]

    subprocess.run(arguments, check=True)


def build(
    builddir: Path, bobfile: Path, do_clean=False, no_compdb=False, symlink_compdb=False
) -> None:
    if do_clean:
        clean(builddir)

    configure(builddir, bobfile, lazy=True)

    p: subprocess.Popen | None
    if not no_compdb:
        p = compdb(builddir, bobfile, dont_symlink=not symlink_compdb, wait=False)

    run_ninja(builddir)

    if p is not None:
        assert p.wait() == 0
