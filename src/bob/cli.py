"""Bob CLI command definitions."""

import subprocess

import rich_click as click

from bob.constants import BOB_BUILD_SUBDIR, DEFAULT_BUILDDIR


@click.group
def cli():
    """The ergonomic Ninja-based build system."""

    from bob.log import setup

    setup()


@cli.command
@click.option(
    "--builddir",
    help="The directory to put the Bob outputs in.",
    default=str(DEFAULT_BUILDDIR),
    show_default=True,
)
@click.option("-f", help="The input Bobfile", default="Bobfile", show_default=True)
@click.option("-c", "--config", multiple=True, help="Supply the given config option")
@click.option(
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring",
)
@click.option(
    "--allow-build-outside-builddir",
    is_flag=True,
    help="Allow building targets which are outside of the build directory.",
)
def configure(**kwargs):
    """Generate the Ninja file to build the project."""

    from bob.commands.configure import configure

    configure(**kwargs)


def complete_targets(ctx, param, incomplete: str):
    p = subprocess.run(
        [
            "ninja",
            "-f",
            DEFAULT_BUILDDIR / BOB_BUILD_SUBDIR / "build.ninja",
            "-t",
            "targets",
            "all",
        ],
        capture_output=True,
    )

    if p.returncode != 0:
        return []

    return [
        line.partition(b":")[0].decode()
        for line in p.stdout.splitlines()
        if line.startswith(incomplete.encode())
        and f"/{BOB_BUILD_SUBDIR}/".encode() not in line
    ]


@cli.command
@click.option(
    "--builddir",
    help="The directory to put the Bob outputs in.",
    default=str(DEFAULT_BUILDDIR),
    show_default=True,
)
@click.option("-f", help="The input Bobfile", default="Bobfile", show_default=True)
@click.option(
    "-v", "--verbose", is_flag=True, help="Show more logs and run Ninja verbosely"
)
@click.option("-c", "--config", multiple=True, help="Supply the given config option")
@click.option("-j", type=int, help="Run this many jobs in parallel (0 means infinity)")
@click.option(
    "-F",
    "--force-reconfigure",
    is_flag=True,
    help="Reconfigure even if the generated Ninja file is up-to-date",
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
@click.option(
    "--no-pretty",
    is_flag=True,
    help="Don't pretty-print Ninja output and progress",
)
@click.option(
    "--no-jobserver",
    is_flag=True,
    help="Don't provide a jobserver",
)
@click.option(
    "--allow-build-outside-builddir",
    is_flag=True,
    help="Allow building targets which are outside of the build directory.",
)
@click.option(
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring",
)
@click.argument("targets", shell_complete=complete_targets, nargs=-1)
def build(**kwargs):
    """Build the project or some of its targets."""

    from bob.commands.build import build

    build(**kwargs)


@cli.command
@click.option(
    "--builddir",
    help="The directory to put the Bob outputs in.",
    default=str(DEFAULT_BUILDDIR),
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
    default=str(DEFAULT_BUILDDIR),
    show_default=True,
)
@click.option("-f", help="The input Bobfile", default="Bobfile", show_default=True)
@click.option(
    "--dont-symlink",
    help="Don't create a symlink in the current directory.",
    is_flag=True,
)
@click.option("-c", "--config", multiple=True, help="Supply the given config option")
def compdb(**kwargs):
    """Create a compilation database for the project."""

    from bob.commands.compdb import compdb

    compdb(**kwargs)


@cli.command
@click.option(
    "--shell", help="The shell to install completions for (default uses $SHELL)"
)
@click.option("-y", help="Edit shell RC files without prompting", is_flag=True)
def completions(**kwargs):
    """Install shell completions for Bob."""

    from bob.commands.completions import completions

    completions(**kwargs)
