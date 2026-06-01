import json
import logging
import time
from pathlib import Path
from typing import Dict, Sequence

from bob.constants import BOB_BUILD_SUBDIR
from bob.core.context import BobContext


def _configs(variables: Sequence[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for variable in variables:
        key, _, value = variable.partition("=")
        result[key] = value
    return result


def _configure(
    builddir: str,
    bobfile_path: Path,
    config: Sequence[str],
    lazy=False,
    use_current_configs=False,
    allow_build_outside_builddir=False,
) -> None:
    start = time.time()

    bob_configs_path = Path(builddir) / BOB_BUILD_SUBDIR / "configs.json"
    build_ninja_path = Path(builddir) / BOB_BUILD_SUBDIR / "build.ninja"
    compdb_ninja_path = Path(builddir) / BOB_BUILD_SUBDIR / "compdb.ninja"

    if use_current_configs:
        assert len(config) == 0
        configs_dict = json.loads(bob_configs_path.read_bytes())
    else:
        configs_dict = _configs(config)

    bob_configs_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_configs = json.dumps(configs_dict, indent=4, sort_keys=True)
    if (
        not bob_configs_path.exists()
        or serialized_configs != bob_configs_path.read_text("utf-8")
    ):
        bob_configs_path.write_text(serialized_configs, "utf-8")

    if lazy and build_ninja_path.exists() and compdb_ninja_path.exists():
        logging.info("Skipped manual configuring, will be called from Ninja if needed")
        return

    with BobContext.create(
        Path(builddir),
        bobfile_path,
        configs_dict,
        build_ninja_path=build_ninja_path,
        compdb_ninja_path=compdb_ninja_path,
        bob_configs_path=bob_configs_path,
        allow_build_outside_builddir=allow_build_outside_builddir,
    ) as context:
        context.configure()

        if len(context.unused_configs) != 0:
            logging.warning(
                "Unused configs: "
                + ", ".join(f'"{config}"' for config in sorted(context.unused_configs))
            )

    end = time.time()
    logging.info(f"Configured in {end - start:.2f} seconds")


def configure(
    builddir: str,
    f: str,
    config: Sequence[str],
    use_current_configs: bool,
    allow_build_outside_builddir: bool,
) -> None:
    _configure(
        builddir,
        Path(f),
        config,
        use_current_configs=use_current_configs,
        allow_build_outside_builddir=allow_build_outside_builddir,
    )
