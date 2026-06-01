import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.prompt import Confirm


def completions(shell: Optional[str], y: bool) -> None:
    if shell is None:
        shell = Path(os.environ["SHELL"]).name

    bob = shutil.which("bob")
    assert bob is not None and Path(bob).resolve() == Path(sys.argv[0]).resolve(), (
        "You must be running a `bob` that is in the PATH to install shell completions!"
    )

    if shell == "bash" or shell == "zsh":
        completions_path = Path.home() / ".config" / "bob" / f"complete.{shell}"
        completions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(completions_path, "w") as f:
            subprocess.check_call(
                f"_BOB_COMPLETE={shell}_source {bob}", stdout=f, shell=True
            )
        print(f"Completion script written to {completions_path}")

        source_line = f". {completions_path.resolve()}\n".encode()

        rcpath = Path.home() / f".{shell}rc"
        contents = b""
        if rcpath.exists():
            contents = rcpath.read_bytes()
            if source_line in contents:
                return

        if not y and not Confirm.ask(f"Source completion script in {rcpath}?"):
            return

        contents += b"\n" + source_line
        rcpath.write_bytes(contents)
        print(f"Updated {rcpath}")
    elif shell == "fish":
        completions_path = Path.home() / ".config" / "fish" / "completions" / "bob.fish"
        completions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(completions_path, "w") as f:
            subprocess.check_call(
                f"_BOB_COMPLETE={shell}_source {bob}", stdout=f, shell=True
            )
        print(f"Completion script written to {completions_path}")
    else:
        raise NotImplementedError(
            f"Shell completions are not yet implemented for {shell}"
        )
