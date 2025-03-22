try:
    import typer
except ImportError:
    raise ImportError(
        "Unable to import typer, to use the engin cli please install the"
        " `cli` extra, e.g. pip install engin[cli]"
    ) from None

from engin.cli.graph import cli as graph_cli

app = typer.Typer()

app.add_typer(graph_cli)
