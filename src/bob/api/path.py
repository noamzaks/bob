from pathlib import Path

from bob.api.rule import RuleInput
from bob.core.context import Context


def read(path: RuleInput.Type, text=False):
    path = RuleInput.resolve(path, path_only=True)

    context = Context.current()
    context.configure_implicit_dependencies.add(path)

    if text:
        return path.read_text()

    return path.read_bytes()


def glob(pattern: str, path: None | str | Path = None) -> list[Path]:
    context = Context.current()

    if path is None:
        path = Path(".")

    if isinstance(path, str):
        path = Path(path)

    context.configure_implicit_dependencies.add(path)
    context.configure_implicit_dependencies.update(
        p for p in path.rglob("*") if p.is_dir()
    )

    return sorted(
        path.glob(pattern),
        key=lambda p: str(p),
    )
