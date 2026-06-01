from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Union


@dataclass(frozen=True)
class PhonyTarget:
    """A meta-target built by a phony rule."""

    name: str


class RootRelativePath:
    """
    A wrapper for paths inside the root of the configuration path.
    If the contained path is absolute, it's interpreted as an absolute path.
    """

    def __init__(
        self,
        value: Union[str, Path, "RootRelativePath"],
        _srcdir: Optional["RootRelativePath"] = None,
        _use_current_source_dir=True,
    ) -> None:
        if isinstance(value, RootRelativePath):
            self.value = value.value
            return

        resolved_srcdir = _srcdir.value if _srcdir is not None else None

        if resolved_srcdir is None:
            from bob.core.context import BobContext

            if _use_current_source_dir and BobContext._instance is not None:
                resolved_srcdir = BobContext._instance.current_source_dir.value
            else:
                resolved_srcdir = Path(".")

        self.value = resolved_srcdir / Path(value)

    def __str__(self) -> str:
        return self.value.__str__()

    def __repr__(self) -> str:
        return self.value.__repr__()

    def __eq__(self, other) -> bool:
        if not isinstance(other, RootRelativePath):
            return self.value == other
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __truediv__(self, other) -> "RootRelativePath":
        return RootRelativePath(self.value / other, _use_current_source_dir=False)

    def is_file(self) -> bool:
        return self.value.is_file()

    def is_dir(self) -> bool:
        return self.value.is_dir()

    @property
    def name(self) -> str:
        return self.value.name

    @property
    def suffix(self) -> str:
        return self.value.suffix

    @property
    def suffixes(self) -> List[str]:
        return self.value.suffixes

    @property
    def stem(self) -> str:
        return self.value.stem

    def with_name(self, name: str) -> "RootRelativePath":
        return RootRelativePath(
            self.value.with_name(name), _use_current_source_dir=False
        )

    def with_stem(self, stem: str) -> "RootRelativePath":
        return RootRelativePath(
            self.value.with_stem(stem), _use_current_source_dir=False
        )

    def with_suffix(self, suffix: str) -> "RootRelativePath":
        return RootRelativePath(
            self.value.with_suffix(suffix), _use_current_source_dir=False
        )

    @property
    def parent(self) -> "RootRelativePath":
        if self.value.parent == self.value:
            raise ValueError(
                f"Cannot get the parent of {self}, escaping build directory!"
            )

        return RootRelativePath(self.value.parent, _use_current_source_dir=False)

    def glob(self, pattern: str) -> Iterable["RootRelativePath"]:
        return (
            RootRelativePath(p, _use_current_source_dir=False)
            for p in self.value.glob(pattern)
        )

    def rglob(self, pattern: str) -> Iterable["RootRelativePath"]:
        return (
            RootRelativePath(p, _use_current_source_dir=False)
            for p in self.value.rglob(pattern)
        )

    def resolve(self) -> Path:
        from bob.core.context import BobContext

        context = BobContext.get()

        return (context.root / self.value).resolve()


@dataclass(frozen=True)
class FileTarget:
    path: RootRelativePath
