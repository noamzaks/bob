from pathlib import Path

DEFAULT_BUILDDIR = Path("build")
BOB_BUILDDIR_SUBDIRECTORY = Path(".bob")
COMPDB_PATH = Path("compile_commands.json")


def get_build_ninja_path(builddir: Path) -> Path:
    return builddir / BOB_BUILDDIR_SUBDIRECTORY / "build.ninja"


def get_compdb_ninja_path(builddir: Path) -> Path:
    return builddir / BOB_BUILDDIR_SUBDIRECTORY / "compdb.ninja"
