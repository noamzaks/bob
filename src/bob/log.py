import logging
import runpy

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as rich_traceback_install

console = Console()


def setup() -> None:
    import click
    import rich_click

    import bob

    rich_traceback_install(console=console, suppress=[click, rich_click, bob, runpy])

    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(show_time=False)],
    )
