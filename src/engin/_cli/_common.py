import importlib
from typing import Never

import typer
from rich import print
from rich.panel import Panel

from engin import Engin


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
        ", e.g. 'app.main:engin'"
    )
}


def get_engin_instance(app: str) -> tuple[str, str, Engin]:
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
