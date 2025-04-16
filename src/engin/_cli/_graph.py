import contextlib
import importlib
import logging
import socketserver
import sys
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from time import sleep
from typing import Annotated, Any

import typer
from rich import print

from engin import Engin, Entrypoint, Invoke, TypeId
from engin._cli._utils import print_error
from engin._dependency import Dependency, Provide, Supply
from engin.ext.asgi import ASGIEngin

try:
    from engin.ext.fastapi import APIRouteDependency
except ImportError:
    APIRouteDependency = None  # type: ignore[assignment,misc]

cli = typer.Typer()

# mute logging from importing of files + engin's debug logging.
logging.disable()

_APP_ORIGIN = ""

_CLI_HELP = {
    "app": (
        "The import path of your Engin instance, in the form 'package:application'"
        ", e.g. 'app.main:engin'"
    )
}


@cli.command(name="graph")
def serve_graph(
    app: Annotated[
        str,
        typer.Argument(help=_CLI_HELP["app"]),
    ],
) -> None:
    """
    Creates a visualisation of your application's dependencies.
    """
    # add cwd to path to enable local package imports
    sys.path.insert(0, "")

    try:
        module_name, engin_name = app.split(":", maxsplit=1)
    except ValueError:
        print_error("Expected an argument of the form 'module:attribute', e.g. 'myapp:engin'")

    global _APP_ORIGIN
    _APP_ORIGIN = module_name.split(".", maxsplit=1)[0]

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print_error(f"unable to find module '{module_name}'")

    try:
        instance = getattr(module, engin_name)
    except AttributeError:
        print_error(f"module '{module_name}' has no attribute '{engin_name}'")

    if not isinstance(instance, Engin):
        print_error(f"'{app}' is not an Engin instance")

    nodes = instance.graph()

    # transform dependencies into mermaid syntax
    dependencies = [
        f"{_render_node(node.parent)} --> {_render_node(node.node)}"
        for node in nodes
        if node.parent is not None
        and not (node.node.block_name and node.node.block_name == node.parent.block_name)
    ]

    blocks = {node.node.block_name for node in nodes if node.node.block_name is not None}

    # group blocks into subgraphs
    for block in blocks:
        dependencies.append(f"subgraph {block}")
        dependencies.extend(
            [
                f"{_render_node(node.parent, False)} --> {_render_node(node.node, False)}"
                for node in nodes
                if node.parent is not None
                and node.node.block_name == block
                and node.parent.block_name == block
            ]
        )
        dependencies.append("end")

    html = (
        _GRAPH_HTML.replace("%%DATA%%", "\n".join(dependencies))
        .replace(
            "%%LEGEND%%",
            ASGI_ENGIN_LEGEND if isinstance(instance, ASGIEngin) else DEFAULT_LEGEND,
        )
        .encode("utf8")
    )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200, "OK")
            self.send_header("Content-type", "html")
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, format: str, *args: Any) -> None:
            return

    def _start_server() -> None:
        with socketserver.TCPServer(("localhost", 8123), Handler) as httpd:
            print("Serving dependency graph on http://localhost:8123")
            httpd.serve_forever()

    server_thread = threading.Thread(target=_start_server)
    server_thread.daemon = True  # Daemonize the thread so it exits when the main script exits
    server_thread.start()

    with contextlib.suppress(KeyboardInterrupt):
        wait_for_interrupt()

    print("Exiting the server...")


def wait_for_interrupt() -> None:
    sleep(10000)


_BLOCK_IDX: dict[str, int] = {}
_SEEN_BLOCKS: list[str] = []


def _render_node(node: Dependency, render_block: bool = True) -> str:
    node_id = id(node)
    md = ""
    style = ""

    # format block name
    if render_block and (n := node.block_name):
        md += f"_{n}_\n"

    node_root_package = node.source_package.split(".", maxsplit=1)[0]
    if node_root_package != _APP_ORIGIN:
        if style:
            style += "E"
        else:
            style = "external"

    if style:
        style = f":::{style}"

    if isinstance(node, Supply):
        md += f"{_short_name(node.return_type_id)}"
        return f'{node_id}("`{md}`"){style}'
    if isinstance(node, Provide):
        md += f"{_short_name(node.return_type_id)}"
        return f'{node_id}["`{md}`"]{style}'
    if isinstance(node, Entrypoint):
        entrypoint_type = node.parameter_types[0]
        md += f"{entrypoint_type}"
        return f'{node_id}[/"`{md}`"\\]{style}'
    if isinstance(node, Invoke):
        md += f"{node.func_name}"
        return f'{node_id}[/"`{md}`"/]{style}'
    if isinstance(node, APIRouteDependency):
        md += f"{node.name}"
        return f'{node_id}[["`{md}`"]]{style}'
    else:
        return f'{node_id}["`{node.name}`"]{style}'


def _short_name(name: TypeId) -> str:
    return str(name).rsplit(".", maxsplit=1)[-1]


_GRAPH_HTML = (Path(__file__).parent / "_graph.html").read_text()

DEFAULT_LEGEND = (
    "0[/Invoke/] ~~~ 1[/Entrypoint\\] ~~~ 2[Provide] ~~~ 3(Supply)"
    ' ~~~ 4["`Block Grouping`"]:::b0 ~~~ 5[External Dependency]:::external'
)
ASGI_ENGIN_LEGEND = DEFAULT_LEGEND + " ~~~ 6[[API Route]]"
