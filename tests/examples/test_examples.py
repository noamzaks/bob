"""Smoke-test every example under `examples/`.

Each leaf directory holding a `Bobfile` is one example. Examples under
`tutorial/`, `howto/` and `reference/` must build cleanly; examples under
`errors/` are expected to fail (they demonstrate diagnostics). Builds run in a
throwaway builddir so the repo stays clean.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def _examples(category: str) -> list[Path]:
    return sorted(p.parent for p in (EXAMPLES / category).glob("*/Bobfile"))


SUCCEED = [d for c in ("tutorial", "howto", "reference") for d in _examples(c)]
FAIL = _examples("errors")


def _build(example: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    # Copy into a scratch dir so the build runs against the example's default
    # builddir without dirtying the repo.
    workdir = tmp_path / example.name
    shutil.copytree(example, workdir)
    return subprocess.run(
        ["bob", "build"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _id(p: Path) -> str:
    return f"{p.parent.name}/{p.name}"


@pytest.mark.parametrize("example", SUCCEED, ids=[_id(p) for p in SUCCEED])
def test_example_builds(example: Path, tmp_path: Path):
    r = _build(example, tmp_path)
    assert r.returncode == 0, f"{_id(example)} failed:\n{r.stdout}{r.stderr}"


@pytest.mark.parametrize("example", FAIL, ids=[_id(p) for p in FAIL])
def test_error_example_fails(example: Path, tmp_path: Path):
    r = _build(example, tmp_path)
    assert r.returncode != 0, (
        f"{_id(example)} unexpectedly succeeded:\n{r.stdout}{r.stderr}"
    )
