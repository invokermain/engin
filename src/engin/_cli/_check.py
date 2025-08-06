from typing import Annotated

import typer
from rich.console import Console

from engin._cli._common import COMMON_HELP, get_engin_instance
from engin.exceptions import TypeNotProvidedError

cli = typer.Typer()


@cli.command(name="check")
def check_dependencies(
    app: Annotated[
        str | None,
        typer.Argument(help=COMMON_HELP["app"]),
    ] = None,
) -> None:
    """
    Validates that all dependencies are satisfied for the given engin instance.

    This command checks that all providers required by invocations and other providers
    are available. It's intended for use in CI to catch missing dependencies.

    Examples:

        1. `engin check`

    Returns:
        Exit code 0 if all dependencies are satisfied.
        Exit code 1 if there are missing providers.
    """
    _, _, instance = get_engin_instance(app)

    console = Console()
    assembler = instance.assembler
    missing_providers = set()

    for invocation in instance._invocations:
        for param_type_id in invocation.parameter_type_ids:
            try:
                assembler._resolve_providers(param_type_id, set())
            except TypeNotProvidedError:
                missing_providers.add(param_type_id)

    if missing_providers:
        sorted_missing = sorted(str(type_id) for type_id in missing_providers)

        console.print("❌ Missing providers found:", style="red bold")
        for missing_type in sorted_missing:
            console.print(f"  • {missing_type}", style="red")

        raise typer.Exit(code=1)
    else:
        console.print("✅ All dependencies are satisfied!", style="green bold")
        raise typer.Exit(code=0)
