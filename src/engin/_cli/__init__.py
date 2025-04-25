import logging
import sys

try:
    import typer
except ImportError:
    raise ImportError(
        "Unable to import typer, to use the engin cli please install the"
        " `cli` extra, e.g. pip install engin[cli]"
    ) from None

from engin._cli._graph import cli as graph_cli
from engin._cli._inspect import cli as inspect_cli

# mute logging from importing of files + engin's debug logging.
logging.disable()

# add cwd to path to enable local package imports
sys.path.insert(0, "")

app = typer.Typer()

app.add_typer(graph_cli)
app.add_typer(inspect_cli)
