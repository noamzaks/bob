from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class PhonyTarget:
    """A meta-target built by a phony rule."""

    name: str


class RootRelativePath:
    """
    A wrapper for paths inside the root of the configuration path.
    If the contained path is absolute, it's interpreted as an absolute path.
    """

    def __init__(self, value: Union[str, Path, "RootRelativePath"]):
        if isinstance(value, RootRelativePath):
            value = value.value

        self.value = Path(value)

    def __str__(self):
        return self.value.__str__()

    def __repr__(self):
        return self.value.__repr__()

    def __eq__(self, other):
        if not isinstance(other, RootRelativePath):
            return self.value == other
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def is_file(self):
        return self.value.is_file()

    def is_dir(self):
        return self.value.is_dir()

    @property
    def name(self):
        return self.value.name

    @property
    def suffix(self):
        return self.value.suffix

    @property
    def suffixes(self):
        return self.value.suffixes

    @property
    def stem(self):
        return self.value.stem

    def with_name(self, name: str):
        return RootRelativePath(self.value.with_name(name))

    def with_stem(self, stem: str):
        return RootRelativePath(self.value.with_stem(stem))

    def with_suffix(self, suffix: str):
        return RootRelativePath(self.value.with_suffix(suffix))

    def __truediv__(self, other):
        return RootRelativePath(self.value / other)

    @property
    def parent(self):
        if self.value.parent == self.value:
            raise ValueError(
                f"Cannot get the parent of {self}, escaping build directory!"
            )

        return RootRelativePath(self.value.parent)

    def glob(self, pattern: str):
        return (RootRelativePath(p) for p in self.value.glob(pattern))

    def rglob(self, pattern: str):
        return (RootRelativePath(p) for p in self.value.rglob(pattern))


@dataclass(frozen=True)
class FileTarget:
    path: RootRelativePath
