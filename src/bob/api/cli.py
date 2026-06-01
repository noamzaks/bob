import logging
from importlib.metadata import version as importlib_version
from typing import Optional

from bob.core.context import BobContext


def config(
    name: str, required: bool = False, default: Optional[str] = None
) -> Optional[str]:
    """
    Get a specific config provided in the command line.

    :param name: The name of the config to get.
    :param required: Whether the config must be provided.
    :param default: Return this value if the config isn't set and ``required`` is not set.
    """

    context = BobContext.get()

    if name in context.unused_configs:
        context.unused_configs.remove(name)

    if name not in context.configs and not required:
        logging.info(f'Unset config "{name}"')
        return default

    return context.configs[name]


def bob_required_version(version: str) -> None:
    """Raise at configure time if the installed Bob version is incompatible."""

    bob_version = importlib_version("bob")

    if "." not in version:
        raise ValueError(
            f"Invalid required version {version} doesn't contain minor requirement!"
        )

    major, minor, *_rest = map(int, version.split("."))
    bob_major, bob_minor, *_rest = map(int, bob_version.split("."))

    if major != bob_major or bob_minor < minor:
        raise Exception(f"Invalid bob version: need {version} but have {bob_version}")


__all__ = [
    "config",
    "bob_required_version",
]
