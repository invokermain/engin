import importlib
import sys
from pathlib import Path

import typer
from rich import print
from rich.panel import Panel
from typing_extensions import Never

from engin import Engin

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def print_error(msg: str) -> Never:
    print(
        Panel(
            title="Error",
            renderable=msg,
            title_align="left",
            border_style="red",
            highlight=True,
        )
    )
    raise typer.Exit(code=1)


COMMON_HELP = {
    "app": (
        "The import path of your Engin instance, in the form 'package:application'"
        ", e.g. 'app.main:engin'. If not provided, will try to use the `default-instance`"
        " value specified in your pyproject.toml"
    )
}


def _find_pyproject_toml() -> Path | None:
    """Find pyproject.toml file starting from current directory and walking up."""
    current_path = Path.cwd()

    for path in [current_path, *current_path.parents]:
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            return pyproject_path

    return None


def _get_default_engin_from_pyproject() -> str | None:
    """Get the default engin instance from pyproject.toml."""
    pyproject_path = _find_pyproject_toml()
    if not pyproject_path:
        return None

    try:
        with Path(pyproject_path).open("rb") as f:
            data = tomllib.load(f)

        tool_section = data.get("tool", {})
        engin_section = tool_section.get("engin", {})
        instance = engin_section.get("default-instance")

        if instance is None:
            return None

        if not isinstance(instance, str):
            print_error("value of `default-instance` is not a string")

        return instance

    except (OSError, tomllib.TOMLDecodeError):
        print_error("invalid toml detected")


NO_APP_FOUND_ERROR = (
    "App path not specified and no default instance specified in pyproject.toml"
)


def get_engin_instance(app: str | None = None) -> tuple[str, str, Engin]:
    """
    Get an Engin instance either from the provided value or from pyproject.toml.

    Args:
        app: Optional string in format 'module:attribute'. If not provided will lookup in
            pyproject.toml.

    Returns:
        Tuple of (module_name, engin_name, engin_instance)

    Raises:
        typer.Exit: If no app is provided and no default instance is specified in the user's
            pyproject.toml.
    """
    if app is None:
        app = _get_default_engin_from_pyproject()
        if app is None:
            print_error(NO_APP_FOUND_ERROR)

    try:
        module_name, engin_name = app.split(":", maxsplit=1)
    except ValueError:
        print_error("Expected an argument of the form 'module:attribute', e.g. 'myapp:engin'")

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print_error(f"Unable to find module '{module_name}'")

    try:
        instance = getattr(module, engin_name)
    except AttributeError:
        print_error(f"Module '{module_name}' has no attribute '{engin_name}'")

    if not isinstance(instance, Engin):
        print_error(f"'{app}' is not an Engin instance")

    return module_name, engin_name, instance
