from pathlib import Path
from typing import List, Optional, Union

from bob.prelude import *

make_rule = Rule(
    "make $arguments",
    always=True,
    restat=True,
    description="MAKE",
    pool="console",
    single_output=False,
)


def make(
    *outputs: Union[str, Path],
    dir=Path("."),
    file: Optional[Path] = None,
    arguments: Optional[List[str]] = None,
    targets: Optional[List[str]] = None,
    implicit: Optional[BuildInput.Type] = None,
    order_only: Optional[BuildInput.Type] = None,
) -> List[FileTarget]:
    """
    Build the given `outputs` using some Makefile.
    The Makefile will always be re-run and it will be restat so dependant targets will be rebuilt if Make rebuilt something.
    :param outputs: The outputs of Make.
    :param dir: The directory to change to when running Make.
    :param arguments: The arguments to pass to Make.
    :param targets: The targets to pass to Make.
    """

    if arguments is None:
        arguments = []

    arguments = ["-C", str(dir)] + arguments

    if file is not None:
        arguments = ["-f", str(file)] + arguments

    if targets is not None:
        arguments += targets

    return make_rule(
        *outputs,
        arguments=arguments,
        implicit=implicit,
        order_only=order_only,
    )


__all__ = ["make"]
