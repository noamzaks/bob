import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Generator

ROOT = Path(__file__).parent.parent.resolve()


@contextmanager
def assert_modification_time_change(
    path: Path, checker: Callable[[float, float], bool]
) -> Generator[None, None, None]:
    before = path.stat().st_mtime

    # Make sure we give the filesystem the opportunity to change the mtime.
    time.sleep(0.1)

    yield

    after = path.stat().st_mtime
    assert checker(before, after)


@contextmanager
def assert_modification_time_does_not_change(path: Path) -> Generator[None, None, None]:
    with assert_modification_time_change(path, lambda before, after: before == after):
        yield


@contextmanager
def assert_modification_time_increases(path: Path) -> Generator[None, None, None]:
    with assert_modification_time_change(path, lambda before, after: before < after):
        yield
