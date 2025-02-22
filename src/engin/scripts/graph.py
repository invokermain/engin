import importlib
import logging
import socketserver
import sys
import threading
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler
from time import sleep
from typing import Any

from engin import Engin
from engin._dependency import Dependency, Provide

# mute logging from importing of files + engin's debug logging.
logging.disable()

args = ArgumentParser(
    prog="engin-graph",
    description="Creates a visualisation of your application's dependencies",
)
args.add_argument(
    "-e", "--exclude", help="a list of packages or module to exclude", default=["engin"]
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
    excluded_modules = parsed.exclude

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
        f"{_render_node(node['parent'])} --> {_render_node(node['node'])}"
        for node in nodes
        if node["parent"] is not None
        and not _should_exclude(node["node"].module, excluded_modules)
    ]

    html = _GRAPH_HTML.replace("%%DATA%%", "\n".join(dependencies)).encode("utf8")

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


def _render_node(node: Dependency) -> str:
    if isinstance(node, Provide):
        return str(node.return_type_id)
    else:
        return node.name


def _should_exclude(module: str, excluded: list[str]) -> bool:
    return any(module.startswith(e) for e in excluded)


_GRAPH_HTML = """
<!doctype html>
<html lang="en">
  <body>
    <pre class="mermaid">
      graph TD
          %%DATA%%
    </pre>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
      let config = { flowchart: { useMaxWidth: false, htmlLabels: true } };
      mermaid.initialize(config);
    </script>
  </body>
</html>
"""
