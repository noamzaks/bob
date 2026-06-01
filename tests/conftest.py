"""A `bob` fixture that runs Bob's CLI on a synthetic Bobfile."""

import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional

import pytest

BOBFILE_START = "from bob.prelude import *\n"
TIMEOUT = 60


@dataclass
class Bob:
    tmp_path: Path

    @property
    def build(self) -> Path:
        return self.tmp_path / "build"

    @property
    def ninja(self) -> Path:
        from bob.constants import BOB_BUILD_SUBDIR

        return self.build / BOB_BUILD_SUBDIR / "build.ninja"

    def write(self, body: str, name: str = "Bobfile") -> Path:
        path = self.tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BOBFILE_START + textwrap.dedent(body).lstrip(), "utf-8")
        return path

    def run(
        self,
        command: str,
        *args: str,
        configs: Optional[Mapping[str, str]] = None,
        assert_succesful: bool = True,
    ) -> subprocess.CompletedProcess:
        arguments = ["bob", command]
        for key, value in (configs or {}).items():
            arguments += ["-c", f"{key}={value}"]
        arguments += list(args)

        r = subprocess.run(
            arguments,
            cwd=self.tmp_path,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )

        if assert_succesful:
            assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        else:
            assert r.returncode != 0, (
                f"expected nonzero exit; got 0. stderr: {r.stderr}\nstdout: {r.stdout}"
            )

        return r

    def output_text(self, name) -> str:
        return self.output_path(name).read_text("utf-8")

    def output_path(self, name) -> Path:
        return self.build / name

    def query(self, target: str) -> Dict[str, List[str]]:
        """Return parsed inputs/outputs/implicit deps for a target via
        `ninja -t query`. Keys: 'input', 'implicit', 'outputs'.

        `target` is resolved against the build dir so callers can pass the
        path they used in `Rule.build(...)` (e.g. "a.txt")."""
        # Ninja indexes targets by their declared path, which is `build/<x>`
        # relative to cwd — not absolute.
        rel = str(self.output_path(target).relative_to(self.tmp_path))
        out = subprocess.run(
            ["ninja", "-f", str(self.ninja), "-t", "query", rel],
            cwd=self.tmp_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        section = None
        result: Dict[str, List[str]] = {"input": [], "implicit": [], "outputs": []}
        for line in out.splitlines():
            stripped = line.strip()
            if stripped.startswith("input:"):
                section = "input"
            elif stripped.startswith("outputs:"):
                section = "outputs"
            elif stripped.startswith("| ") and section == "input":
                # `| dep` lines under `input:` are implicit deps.
                result["implicit"].append(stripped[2:])
            elif stripped and section is not None:
                result[section].append(stripped)
        return result


def assert_output_contains_needles(
    r: subprocess.CompletedProcess, *needles: str
) -> None:
    blob = (r.stdout + r.stderr).lower()
    for n in needles:
        assert n.lower() in blob, f"missing {n!r} in:\n{r.stdout}{r.stderr}"


@pytest.fixture
def bob(tmp_path: Path) -> Bob:
    return Bob(tmp_path)
