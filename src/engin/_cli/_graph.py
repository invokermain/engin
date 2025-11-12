import contextlib
import json
import socketserver
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from time import sleep
from typing import Annotated, Any

import typer
from rich import print

from engin import Engin, Entrypoint, Invoke, TypeId
from engin._cli._common import COMMON_HELP, get_engin_instance
from engin._dependency import Dependency, Provide, Supply
from engin._graph import Node
from engin.extensions.asgi import ASGIEngin

try:
    from engin.extensions.fastapi import APIRouteDependency
except ImportError:
    APIRouteDependency = None  # type: ignore[assignment,misc]

cli = typer.Typer()


_APP_ORIGIN = ""


@cli.command(name="graph")
def serve_graph(
    app: Annotated[
        str | None,
        typer.Argument(help=COMMON_HELP["app"]),
    ] = None,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to serve the graph on."),
    ] = 8123,
) -> None:
    """
    Creates a visualisation of your application's dependencies.

    Examples:

        1. `engin graph`
        2. `engin graph app.main:engin -p 8123`
    """
    module_name, _, instance = get_engin_instance(app)

    global _APP_ORIGIN
    _APP_ORIGIN = module_name.split(".", maxsplit=1)[0]

    nodes = instance.graph()

    # Generate JSON data for interactive graph
    graph_data = _generate_graph_data(nodes, instance)

    html = _GRAPH_HTML.replace("%%GRAPH_DATA%%", json.dumps(graph_data, indent=2)).encode(
        "utf8"
    )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200, "OK")
            self.send_header("Content-type", "html")
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, format: str, *args: Any) -> None:
            return

    shutdown_event = threading.Event()

    def _shutdown_thread(server: socketserver.TCPServer) -> None:
        shutdown_event.wait()  # Wait until the shutdown event is set
        server.shutdown()  # This will cause server.serve_forever() to exit

    def _start_server() -> None:
        with socketserver.TCPServer(("localhost", port), Handler) as httpd:
            print(f"Serving dependency graph on http://localhost:{port}")
            shutdown_thread = threading.Thread(target=_shutdown_thread, args=(httpd,))
            shutdown_thread.start()  # Start shutdown event listener thread
            httpd.serve_forever()  # Will only return when shutdown() is called
            shutdown_thread.join()  # Ensure shutdown thread has finished

    server_thread = threading.Thread(target=_start_server)
    server_thread.start()

    with contextlib.suppress(KeyboardInterrupt):
        wait_for_interrupt()

    print("Exiting the server...")
    shutdown_event.set()  # notify the shutdown
    server_thread.join()  # Wait for the server thread to finish


def wait_for_interrupt() -> None:
    sleep(10000)


def _generate_graph_data(nodes: list[Node], instance: Engin) -> dict[str, Any]:
    """Generate JSON data structure for interactive graph rendering."""
    all_deps = set()
    for node in nodes:
        all_deps.add(node.node)
        if node.parent:
            all_deps.add(node.parent)

    # Generate node data
    node_data = []
    for dep in all_deps:
        node_info = _get_node_info(dep)
        node_data.append(node_info)

    # Generate edge data
    edge_data = [
        {
            "from": f"n{id(node.parent)}",
            "to": f"n{id(node.node)}",
            "from_block": node.parent.block_name,
            "to_block": node.node.block_name,
        }
        for node in nodes
        if node.parent is not None
    ]

    # Get block information
    blocks = list({node.node.block_name for node in nodes if node.node.block_name is not None})

    # Generate legend
    legend = ASGI_ENGIN_LEGEND if isinstance(instance, ASGIEngin) else DEFAULT_LEGEND

    return {
        "nodes": node_data,
        "edges": edge_data,
        "blocks": blocks,
        "legend": legend,
        "app_origin": _APP_ORIGIN,
    }


def _get_node_info(node: Dependency) -> dict[str, Any]:
    """Extract node information for JSON representation."""
    node_id = f"n{id(node)}"  # Add 'n' prefix to match mermaid node IDs
    label = ""
    style_classes = []

    # Determine if external
    node_root_package = node.source_package.split(".", maxsplit=1)[0]
    is_external = node_root_package != _APP_ORIGIN
    if is_external:
        style_classes.append("external")

    # Collect detailed information for tooltips
    details: dict[str, Any] = {
        "full_name": node.name,
        "source_module": node.source_module,
        "source_package": node.source_package,
        "parameters": [],
        "return_type": None,
        "scope": None,
    }

    # Get parameter information
    if hasattr(node, "parameter_type_ids"):
        details["parameters"] = [str(param_id) for param_id in node.parameter_type_ids]

    # Determine node type and extract specific details
    if isinstance(node, Supply):
        node_type = "Supply"
        label += f"{_short_name(node.return_type_id)}"
        shape = "round"
        details["return_type"] = str(node.return_type_id)
        if hasattr(node, "_value"):
            details["value_type"] = type(node._value).__name__
    elif isinstance(node, Provide):
        node_type = "Provide"
        label += f"{_short_name(node.return_type_id)}"
        shape = "rect"
        details["return_type"] = str(node.return_type_id)
        details["factory_function"] = node.func_name
        if node.scope:
            details["scope"] = node.scope
            style_classes.append(f"scope-{node.scope}")
        if node.is_multiprovider:
            details["multiprovider"] = True
            style_classes.append("multi")
    elif isinstance(node, Entrypoint):
        node_type = "Entrypoint"
        entrypoint_type = node.parameter_type_ids[0]
        label += f"{entrypoint_type}"
        shape = "trapezoid"
        details["entrypoint_type"] = str(entrypoint_type)
    elif isinstance(node, Invoke):
        node_type = "Invoke"
        label += f"{node.func_name}"
        shape = "trapezoid"
        details["function"] = node.func_name
    elif APIRouteDependency is not None and isinstance(node, APIRouteDependency):
        node_type = "APIRoute"
        label += f"{node.name}"
        shape = "subroutine"
        if hasattr(node, "route"):
            details["methods"] = (
                list(node.route.methods) if hasattr(node.route, "methods") else []
            )
            details["path"] = getattr(node.route, "path", "")
    else:
        node_type = "Other"
        label += f"{node.name}"
        shape = "rect"

    return {
        "id": node_id,
        "label": label,
        "type": node_type,
        "external": is_external,
        "block": node.block_name,
        "shape": shape,
        "style_classes": style_classes,
        "source_module": node.source_module,
        "source_package": node.source_package,
        "details": details,
    }


def _short_name(name: TypeId) -> str:
    return str(name).rsplit(".", maxsplit=1)[-1]


_GRAPH_HTML = (Path(__file__).parent / "_graph.html").read_text()

DEFAULT_LEGEND = (
    "0[/Invoke/] ~~~ 1[/Entrypoint\\] ~~~ 2[Provide] ~~~ 3(Supply)"
    ' ~~~ 4["`Block Grouping`"]:::b0 ~~~ 5[External Dependency]:::external'
)
ASGI_ENGIN_LEGEND = DEFAULT_LEGEND + " ~~~ 6[[API Route]]"
