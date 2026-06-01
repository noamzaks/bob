import subprocess
import sys
from pathlib import Path
from typing import Sequence

from bob.commands.configure import _configure
from bob.constants import BOB_BUILD_SUBDIR, COMPDB_NAME


def _compdb(builddir: str, dont_symlink=False) -> None:
    build_compdb_path = Path(builddir) / COMPDB_NAME

    with open(build_compdb_path, "w") as f:
        returncode = subprocess.call(
            [
                "ninja",
                "-f",
                Path(builddir) / BOB_BUILD_SUBDIR / "compdb.ninja",
                "-t",
                "compdb",
            ],
            stdout=f,
        )
        if returncode != 0:
            sys.exit(returncode)

    if not dont_symlink:
        COMPDB_NAME.unlink(missing_ok=True)
        COMPDB_NAME.symlink_to(build_compdb_path)


def compdb(
    builddir: str,
    f: str,
    config: Sequence[str],
    dont_symlink: bool,
) -> None:
    _configure(builddir, Path(f), config, allow_build_outside_builddir=True)
    _compdb(builddir, dont_symlink=dont_symlink)
