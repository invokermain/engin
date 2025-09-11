import threading
import time
from datetime import datetime

import requests
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from engin import Engin, Entrypoint, Invoke, Supply
from engin._cli._graph import cli
from tests.deps import ABlock


def invoke_something(data: datetime) -> None: ...


engin = Engin(
    ABlock,
    Supply(["3"]),
    Invoke(invoke_something),
    Entrypoint(list[str]),
)
runner = CliRunner()


def test_cli_graph(mocker: MockerFixture) -> None:
    cli_thread = None
    cli_result = None
    interrupt_event = threading.Event()

    def run_cli():
        nonlocal cli_result
        cli_result = runner.invoke(app=cli, args=["tests.cli.test_graph:engin"])

    def mock_wait_for_interrupt():
        interrupt_event.wait()
        raise KeyboardInterrupt

    mocker.patch("engin._cli._graph.wait_for_interrupt", side_effect=mock_wait_for_interrupt)

    try:
        cli_thread = threading.Thread(target=run_cli)
        cli_thread.start()

        time.sleep(0.5)

        response = requests.get("http://localhost:8123")
        assert response.status_code == 200

        interrupt_event.set()
        cli_thread.join(timeout=2)

    finally:
        if cli_thread and cli_thread.is_alive():
            interrupt_event.set()
            cli_thread.join(timeout=1)

    assert cli_result is not None
    assert cli_result.exit_code == 0


def test_cli_invalid_app_path() -> None:
    result = runner.invoke(app=cli, args=["tests.cli.foo"])
    assert result.exit_code == 1
    assert "module" in result.output


def test_cli_invalid_app_path_2() -> None:
    result = runner.invoke(app=cli, args=["tests.cli.foo:engin"])
    assert result.exit_code == 1
    assert "module" in result.output


def test_cli_invalid_app_attribute() -> None:
    result = runner.invoke(app=cli, args=["tests.cli.test_graph:foo"])
    assert result.exit_code == 1
    assert "no attribute" in result.output


def test_cli_invalid_app_instance() -> None:
    result = runner.invoke(app=cli, args=["tests.cli.test_graph:runner"])
    assert result.exit_code == 1
    assert "Engin" in result.output
