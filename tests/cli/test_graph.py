from pytest_mock import MockerFixture
from typer.testing import CliRunner

from engin import Engin, Entrypoint
from engin.cli.graph import cli
from tests.deps import ABlock

engin = Engin(ABlock, Entrypoint(list[float]))
runner = CliRunner()


def test_cli_graph(mocker: MockerFixture) -> None:
    mocker.patch("engin.cli.graph.wait_for_interrupt", side_effect=KeyboardInterrupt)
    result = runner.invoke(app=cli, args=["tests.cli.test_graph:engin"])
    assert result.exit_code == 0
