from pathlib import Path
from typing import Union

from bob.core.context import BobContext
from bob.core.scope import AttributeScope
from bob.core.targets import RootRelativePath


def srcdir() -> RootRelativePath:
    """Returns the root-relative path to the configuration's current directory."""

    context = BobContext.get()
    return RootRelativePath(context.current_source_dir)


def builddir() -> RootRelativePath:
    """Returns the path to the current build directory."""

    context = BobContext.get()
    return RootRelativePath(context.current_build_dir)


def src_recurse(path: Union[str, Path]) -> AttributeScope:
    """Return a scope where the current source directory is recursed into the given path."""

    context = BobContext.get()
    return AttributeScope(
        context, {"current_source_dir": context.current_source_dir / path}
    )


def build_recurse(path: Union[str, Path]) -> AttributeScope:
    """Return a scope where the current build directory is recursed into the given path."""

    context = BobContext.get()
    return AttributeScope(
        context, {"current_build_dir": context.current_build_dir / path}
    )


def read(
    path: Union[RootRelativePath, Path, str], text: bool = False
) -> Union[str, bytes]:
    """Reads the given file (demanding reconfiguration when it changes)."""

    p = RootRelativePath(path)
    context = BobContext.get()
    assert context.configure_implicit_dependencies is not None
    context.configure_implicit_dependencies.add(p)

    if text:
        return p.resolve().read_text()
    return p.resolve().read_bytes()


def glob(pattern: str, path: Union[None, RootRelativePath, Path, str] = None) -> list:
    """Find all files matching the given `pattern` in the given `path`."""

    context = BobContext.get()
    resolved_path = (
        context.current_source_dir if path is None else RootRelativePath(path)
    )
    assert context.configure_implicit_dependencies is not None
    context.configure_implicit_dependencies.add(resolved_path)
    context.configure_implicit_dependencies.update(
        p for p in resolved_path.rglob("*") if p.is_dir()
    )
    return [
        Path(f)
        for f in sorted(
            str(f.value.relative_to(context.current_source_dir.value))
            for f in resolved_path.glob(pattern)
            if f.is_file()
        )
    ]


__all__ = [
    "RootRelativePath",
    "srcdir",
    "builddir",
    "src_recurse",
    "build_recurse",
    "read",
    "glob",
]
