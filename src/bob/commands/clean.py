import logging
import shutil
from pathlib import Path

from bob.constants import BOB_BUILD_SUBDIR, COMPDB_NAME


def _clean(builddir: str, force=False) -> None:
    builddir_path = Path(builddir)
    if not builddir_path.exists():
        return

    if not force and not (builddir_path / BOB_BUILD_SUBDIR).exists():
        logging.warning(
            f"Not deleting {builddir} since it doesn't seem to be a Bob build directory!"
        )
        return

    if (
        COMPDB_NAME.is_symlink()
        and Path(builddir).resolve() in COMPDB_NAME.resolve().parents
    ):
        COMPDB_NAME.unlink(missing_ok=True)

    shutil.rmtree(builddir)


def clean(builddir: str, force: bool) -> None:
    _clean(builddir, force=force)
