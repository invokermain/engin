from datetime import datetime

from fastapi import APIRouter
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from engin import Engin, Entrypoint, Invoke, Supply
from engin._cli._graph import cli
from tests.deps import ABlock


def invoke_something(dt: datetime) -> None: ...


api_router = APIRouter()


@api_router.get("/hello")
def get_hello() -> str:
    return "hello"


engin = Engin(
    ABlock,
    Supply("3"),
    Supply(api_router),
    Invoke(invoke_something),
    Entrypoint(list[float]),
)
runner = CliRunner()


def test_cli_graph(mocker: MockerFixture) -> None:
    mocker.patch("engin._cli._graph.wait_for_interrupt", side_effect=KeyboardInterrupt)
    result = runner.invoke(app=cli, args=["tests.cli.test_graph:engin"])
    assert result.exit_code == 0


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
