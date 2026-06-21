import os
from pathlib import Path

import pytest


@pytest.fixture()
def builddir() -> Path:
    return Path("build")


@pytest.fixture(autouse=True)
def unique_tmp_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    result = tmp_path_factory.mktemp("bob")
    os.chdir(result)
    return result


@pytest.fixture()
def bobfile(unique_tmp_path: Path) -> Path:
    return unique_tmp_path / "Bobfile"


def pytest_addoption(parser: pytest.Parser) -> None:
    configure = parser.getgroup("configure")
    configure.addoption(
        "--update", action="store_true", help="Update the configure test cases"
    )
