from typer.testing import CliRunner

from engin import Engin
from engin._cli._inspect import cli
from tests.deps import ABlock

engin = Engin(ABlock)
runner = CliRunner()


def test_cli_inspect() -> None:
    result = runner.invoke(
        app=cli,
        args=["tests.cli.test_inspect:engin", "--type", "float[]", "--verbose"],
    )
    assert result.exit_code == 0
