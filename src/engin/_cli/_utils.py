from typing import Never

import typer
from rich import print
from rich.panel import Panel


def print_error(msg: str) -> Never:
    print(
        Panel(
            title="Error",
            renderable=msg.capitalize(),
            title_align="left",
            border_style="red",
            highlight=True,
        )
    )
    raise typer.Exit(code=1)
