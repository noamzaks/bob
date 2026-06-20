import os
from pathlib import Path

import rich_click as click

from bob.constants import DEFAULT_BUILDDIR


@click.group
def cli() -> None:
    """The ergonomic Ninja-based build system."""
    from bob.log import setup

    setup()


@cli.command()
@click.option(
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile",
    default=Path("Bobfile"),
    show_default=True,
)
@click.option("--clean", "do_clean", is_flag=True, help="Clean before building")
@click.option(
    "--no-compdb", is_flag=True, help="Don't create a compilation DB for this build."
)
@click.option(
    "--symlink-compdb",
    is_flag=True,
    help="Create a symlink to the compilation DB in the current directory",
)
def build(**kwargs) -> None:
    """Build the given Bob project."""

    from bob.commands.build import build

    build(**kwargs)


@cli.command
@click.option(
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "--force",
    help="Remove the build directory even if it doesn't match a Bob build directory.",
    is_flag=True,
)
def clean(**kwargs):
    """Clean all built files."""

    from bob.commands.clean import clean

    clean(**kwargs)


@cli.command
@click.option(
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile",
    default=Path("Bobfile"),
    show_default=True,
)
@click.option(
    "--dont-symlink",
    help="Don't create a symlink in the current directory.",
    is_flag=True,
)
def compdb(**kwargs):
    """Create a compilation database for the project."""

    from bob.commands.compdb import compdb

    compdb(**kwargs)


@cli.command
@click.option(
    "--shell",
    help="The shell to install completions for.",
    default=Path(os.environ["SHELL"]).name if "SHELL" in os.environ else None,
    show_default=True,
)
def completions(**kwargs) -> None:
    """Install shell completions for Bob."""

    from bob.commands.completions import completions

    completions(**kwargs)
