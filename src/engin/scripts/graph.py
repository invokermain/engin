import importlib
import logging
import socketserver
import sys
import threading
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler
from time import sleep
from typing import Any

from engin import Engin, Entrypoint, Invoke
from engin._dependency import Dependency, Provide, Supply
from engin.ext.asgi import ASGIEngin
from engin.ext.fastapi import APIRouteDependency

# mute logging from importing of files + engin's debug logging.
logging.disable()

args = ArgumentParser(
    prog="engin-graph",
    description="Creates a visualisation of your application's dependencies",
)
args.add_argument(
    "app",
    help=(
        "the import path of your Engin instance, in the form "
        "'package:application', e.g. 'app.main:engin'"
    ),
)


def serve_graph() -> None:
    # add cwd to path to enable local package imports
    sys.path.insert(0, "")

    parsed = args.parse_args()

    app = parsed.app

    try:
        module_name, engin_name = app.split(":", maxsplit=1)
    except ValueError:
        raise ValueError(
            "Expected an argument of the form 'module:attribute', e.g. 'myapp:engin'"
        ) from None

    module = importlib.import_module(module_name)

    try:
        instance = getattr(module, engin_name)
    except LookupError:
        raise LookupError(f"Module '{module_name}' has no attribute '{engin_name}'") from None

    if not isinstance(instance, Engin):
        raise TypeError(f"'{app}' is not an Engin instance")

    nodes = instance.graph()

    # transform dependencies into mermaid syntax
    dependencies = [
        f"{_render_node(node.parent)} --> {_render_node(node.node)}"
        for node in nodes
        if node.parent is not None
    ]

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

    try:
        sleep(10000)
    except KeyboardInterrupt:
        print("Exiting the server...")


_BLOCK_IDX: dict[str, int] = {}
_SEEN_BLOCKS: list[str] = []


def _render_node(node: Dependency) -> str:
    node_id = id(node)
    md = ""
    style = ""

    # format block name
    if n := node.block_name:
        md += f"_{n}_\n"
        if n not in _BLOCK_IDX:
            _BLOCK_IDX[n] = len(_SEEN_BLOCKS) % 8
            _SEEN_BLOCKS.append(n)
        style = f":::b{_BLOCK_IDX[n]}"

    if isinstance(node, Supply):
        md += f"{node.return_type_id}"
        return f'{node_id}("`{md}`"){style}'
    if isinstance(node, Provide):
        md += f"{node.return_type_id}"
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


_GRAPH_HTML = """
<!doctype html>
<html lang="en">
  <body>
    <div style="border-style:outset">
        <p>LEGEND</p>
        <pre class="mermaid">
          graph LR
            %%LEGEND%%
            classDef b0 fill:#7fc97f;
        </pre>
    </div>
    <pre class="mermaid">
      graph TD
          %%DATA%%
          classDef b0 fill:#7fc97f;
          classDef b1 fill:#beaed4;
          classDef b2 fill:#fdc086;
          classDef b3 fill:#ffff99;
          classDef b4 fill:#386cb0;
          classDef b5 fill:#f0027f;
          classDef b6 fill:#bf5b17;
          classDef b7 fill:#666666;
    </pre>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
      let config = { flowchart: { useMaxWidth: false, htmlLabels: true } };
      mermaid.initialize(config);
    </script>
  </body>
</html>
"""

DEFAULT_LEGEND = (
    "0[/Invoke/] ~~~ 1[/Entrypoint\\] ~~~ 2[Provide] ~~~ 3(Supply)"
    ' ~~~ 4["`Block Grouping`"]:::b0'
)
ASGI_ENGIN_LEGEND = DEFAULT_LEGEND + " ~~~ 5[[API Route]]"
