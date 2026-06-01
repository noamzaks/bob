"""Bob CLI command implementations."""

import logging
import os
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, nullcontext
from pathlib import Path
from typing import Optional, Sequence

from bob.commands.clean import _clean
from bob.commands.compdb import _compdb
from bob.commands.configure import _configure
from bob.constants import BOB_BUILD_SUBDIR
from bob.log import console

DESCRIPTION_WIDTH = 10

PRETTY_COLORS = (
    "yellow",
    "blue",
    "green",
    "magenta",
    "cyan",
    "bright_yellow",
    "bright_blue",
    "bright_green",
    "bright_magenta",
    "bright_cyan",
)


NINJA_OUTPUT_BLACKLIST = {f"/{BOB_BUILD_SUBDIR}/", "ninja: Jobserver mode detected"}


def _pretty_print(p: subprocess.Popen, separator: str, verbose: bool) -> None:
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.text import Text

    assert p.stdout is not None

    with Progress(
        SpinnerColumn(),
        MofNCompleteColumn(),
        TextColumn("{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("", total=None)
        while line := p.stdout.readline():
            assert isinstance(line, bytes)

            try:
                decoded = line.decode().removeprefix("\n").removesuffix("\n")
            except UnicodeDecodeError:
                sys.stdout.buffer.write(line)
                continue

            if any(b in decoded for b in NINJA_OUTPUT_BLACKLIST):
                continue

            try:
                parameters, _, command = decoded.strip().partition(separator)
                finished_edges, total_edges = [int(x) for x in parameters.split(",")]
            except ValueError:
                console.print(decoded, highlight=False, markup=False)
                continue

            description, _, outputs = command.partition(" ")

            color = (
                PRETTY_COLORS[ord(description[0]) % len(PRETTY_COLORS)]
                if not verbose
                else "white"
            )

            console.print(
                Text(description.ljust(DESCRIPTION_WIDTH), style=color)
                + Text(" " + outputs, style="white"),
                highlight=False,
                markup=False,
            )

            command = description + " " + outputs

            progress.update(
                task_id,
                description=command,
                completed=finished_edges,
                total=total_edges,
            )


def build(
    builddir: str,
    targets: Sequence[str],
    f: str,
    config: Sequence[str],
    verbose: bool,
    j: Optional[int],
    do_clean: bool,
    no_compdb: bool,
    symlink_compdb: bool,
    force_reconfigure: bool,
    no_pretty: bool,
    no_jobserver: bool,
    allow_build_outside_builddir: bool,
    use_current_configs: bool,
) -> None:
    if j == 0:
        no_jobserver = True

    if no_jobserver or "MAKEFLAGS" in os.environ:
        ctx = nullcontext()
        tmp_dir = None
    else:
        from bob.jobserver import jobserver

        resolved_j = os.cpu_count() if j is None else j
        assert resolved_j is not None

        ctx = ExitStack()
        tmp_dir = tempfile.TemporaryDirectory()
        ctx.enter_context(tmp_dir)
        fifo_path = Path(tmp_dir.name) / "jobserver"
        ctx.enter_context(jobserver(resolved_j, fifo_path))
        j = None

    with ctx:
        start = time.time()

        if verbose:
            logging.getLogger().setLevel(logging.INFO)

        if do_clean:
            _clean(builddir)

        _configure(
            builddir,
            Path(f),
            config,
            lazy=not do_clean and not force_reconfigure,
            use_current_configs=use_current_configs,
            allow_build_outside_builddir=allow_build_outside_builddir,
        )

        if not no_compdb:
            _compdb(builddir, dont_symlink=not symlink_compdb)

        arguments = [
            "ninja",
            "-f",
            Path(builddir) / BOB_BUILD_SUBDIR / "build.ninja",
            *targets,
        ]
        if verbose:
            arguments.append("-v")
        if j is not None:
            arguments += ["-j", str(j)]

        if no_pretty:
            p = subprocess.run(arguments)
        else:
            separator = " BOB_NINJA_SEPARATOR "

            env = os.environ.copy()
            env["NINJA_STATUS"] = f"%f,%t{separator}"
            env["CLICOLOR_FORCE"] = "1"
            p = subprocess.Popen(
                arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
            )
            _pretty_print(p, separator=separator, verbose=verbose)
            p.wait()

        end = time.time()

        logging.info(f"Built in {end - start:.2f} seconds")

        sys.exit(p.returncode)
