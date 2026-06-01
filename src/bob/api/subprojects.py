import logging
import runpy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type, TypeVar, Union, overload

from bob.core.context import BobContext, Exports
from bob.core.targets import RootRelativePath
from bob.utilities import get_caller_frame

T = TypeVar("T")


def _get_bobfile(path: Union[str, Path]) -> Tuple[Path, str]:
    resolved_path = Path(path)
    p = RootRelativePath(path)
    if p.is_dir():
        return resolved_path, "Bobfile"
    return resolved_path.parent, resolved_path.name


def export(**variables: Any) -> None:
    """Export variables to anyone calling this file using `subbob`."""

    context = BobContext.get()
    context.exports.update(variables)


@overload
def use(
    name: str, type: Type[T], optional: bool = False, default: Optional[T] = None
) -> T: ...


@overload
def use(
    name: str, type: None = None, optional: bool = False, default: Any = None
) -> Any: ...


def use(
    name: str,
    type: Optional[Type[T]] = None,
    optional: bool = False,
    default: Any = None,
) -> Union[T, Any]:
    """
    Use the given name provided by anyone calling this file using `subbob`.

    :param name: The name of the provided value.
    :param type: An optional class to verify the value is an instance of.
    :param optional: Succeed even if the value wasn't provided.
    :param default: Return this value if the value wasn't provided and ``optional`` is set.
    """

    context = BobContext.get()

    if optional and name not in context.provides:
        return default

    result = context.provides[name]

    if type is not None and not isinstance(result, type):
        raise TypeError()

    return result


def subbob(
    path: Union[str, Path],
    configs: Optional[Dict[str, Any]] = None,
    change_build_dir: Union[bool, str, Path] = True,
    provides: Optional[Dict[str, Any]] = None,
) -> Exports:
    """
    Execute another Bobfile in a separate scope.

    :param path: Path to the directory containing the Bobfile, or the Bobfile itself.
    :param configs: Configs used for the sub-Bobfile.
    :param change_build_dir: Whether to recurse into a build subdirectory, optionally with a custom subpath.
    :param provides: Values to provide to the sub-Bobfile, consumed there with `use`.
    """

    if configs is None:
        configs = {}

    if provides is None:
        provides = {}

    context = BobContext.get()
    context._backup()

    try:
        path, bobname = _get_bobfile(path)

        resolved_change_build_dir = (
            path if change_build_dir is True else change_build_dir
        )

        if resolved_change_build_dir:
            context.current_build_dir /= resolved_change_build_dir

        context.current_source_dir /= path
        context.configs = configs
        context.exports = {}
        context.provides = provides
        context.unused_configs = set(configs.keys())

        context.configure(bobname)
        result = context.get_exports()

        if len(context.unused_configs) != 0:
            logging.warning(
                f'Unused configs in subbob("{path}"): '
                + ", ".join(f'"{c}"' for c in sorted(context.unused_configs))
            )
    finally:
        context._restore()

    return result


def include(
    path: Union[str, Path],
    change_build_dir: Union[bool, Path] = False,
    change_source_dir: Union[bool, Path] = True,
) -> None:
    """
    Include the Bobfile in the given path by executing it in the caller's scope.

    :param path: Path to the directory containing the Bobfile, or the Bobfile itself.
    :param change_build_dir: Whether to recurse the build directory, optionally with a custom subpath.
    :param change_source_dir: Whether to recurse the source directory, optionally with a custom subpath.
    """

    context = BobContext.get()
    original_source_dir = context.current_source_dir
    original_build_dir = context.current_build_dir

    try:
        path, bobname = _get_bobfile(path)
        bobfile = (RootRelativePath(path) / bobname).resolve()

        resolved_change_build_dir = (
            path if change_build_dir is True else change_build_dir
        )
        resolved_change_source_dir = (
            path if change_source_dir is True else change_source_dir
        )

        if resolved_change_build_dir:
            context.current_build_dir /= resolved_change_build_dir
        if resolved_change_source_dir:
            context.current_source_dir /= resolved_change_source_dir

        caller_frame = get_caller_frame()
        caller_frame.f_locals.update(
            runpy.run_path(str(bobfile), caller_frame.f_globals | caller_frame.f_locals)
        )
        assert context.configure_implicit_dependencies is not None
        context.configure_implicit_dependencies.add(RootRelativePath(bobfile))
    finally:
        context.current_source_dir = original_source_dir
        context.current_build_dir = original_build_dir


__all__ = [
    "subbob",
    "include",
    "export",
    "use",
]
