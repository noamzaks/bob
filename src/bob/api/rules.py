import logging
import subprocess
import sys
from types import FrameType
from typing import Optional, Union

from bob.constants import BOB_BUILD_SUBDIR
from bob.core import FileTarget, PhonyTarget, Rule, Variable, phony
from bob.core.context import BobContext
from bob.core.provider import RuleProvider
from bob.core.rule import BuildInput
from bob.utilities import get_caller_frame


class GenerateRule(Rule):
    def __init__(
        self,
        command: str,
        depfile: Optional[str] = None,
        deps: Optional[str] = None,
        compile_command: Optional[str] = None,
        description: Optional[str] = None,
        generator: Optional[bool] = None,
        pool: Optional[str] = None,
        implicit: Optional[BuildInput.Type] = None,
        order_only: Optional[BuildInput.Type] = None,
        implicit_outputs: Optional[BuildInput.Type] = None,
        single_input: bool = False,
        caller_frame: Optional[FrameType] = None,
        **variables: BuildInput.Type,
    ):
        """Create a rule that always runs the given `command` and stores its output only if it changed."""

        if description is None:
            description = "GEN"

        super().__init__(
            command=f"(({command}) > $out.new && cmp -s $out $out.new || mv $out.new $out); rm -f $out.new",
            depfile=depfile,
            deps=deps,
            compile_command=compile_command,
            description=description,
            restat=True,
            generator=generator,
            pool=pool,
            always=True,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
            single_input=single_input,
            single_output=True,
            _caller_frame=caller_frame or get_caller_frame(),
            **variables,
        )


def variable(name: str, *rules: Union[Rule, RuleProvider]) -> Variable:
    """Return an object for modifying the variable called `name` in each of the `rules`."""

    return Variable(*rules, name=name)


def shell(command: str, text: bool = True) -> Union[str, bytes]:
    """Run the given shell command during configuration."""

    context = BobContext.get()
    name = BOB_BUILD_SUBDIR / f"bob-shell-{context.shell_index}"
    context.shell_index += 1

    generated: FileTarget = GenerateRule(command).build(name)

    assert context.configure_implicit_dependencies is not None
    context.configure_implicit_dependencies.add(generated.path)

    p = subprocess.run(command, shell=True, capture_output=True)
    if p.returncode != 0:
        sys.stdout.buffer.write(p.stdout)
        sys.stderr.buffer.write(p.stderr)
        logging.error(f"Executing {command} failed")
        sys.exit(p.returncode)

    output = p.stdout
    output_file = generated.path.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(output)

    if text:
        return output.decode()
    return output


__all__ = [
    "BuildInput",
    "Rule",
    "FileTarget",
    "GenerateRule",
    "phony",
    "PhonyTarget",
    "variable",
    "shell",
]
