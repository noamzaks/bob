from pathlib import Path

from bob.constants import get_build_ninja_path
from bob.core.context import Context


def configure(builddir: Path, bobfile: Path, lazy=False) -> None:
    if lazy and get_build_ninja_path(builddir).exists():
        return

    with Context(builddir) as context:
        context.evaluate(bobfile)
