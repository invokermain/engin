from typer.testing import CliRunner

from engin import Engin, Invoke, Provide
from engin._cli._check import cli
from tests.deps import ABlock, make_str

satisfied_engin = Engin(ABlock)


def needs_missing_dependency(missing_type: int) -> None:
    pass


unsatisfied_engin = Engin(
    Provide(make_str),
    Invoke(needs_missing_dependency),
)


def needs_complex_type(custom_type: dict[str, int]) -> None:
    pass


complex_unsatisfied_engin = Engin(
    ABlock,
    Invoke(needs_complex_type),
)

runner = CliRunner()


def test_check_all_dependencies_satisfied():
    result = runner.invoke(
        app=cli,
        args=["tests.cli.test_check:satisfied_engin"],
    )
    assert result.exit_code == 0
    assert "✅ All dependencies are satisfied!" in result.output


def test_check_missing_dependencies():
    result = runner.invoke(
        app=cli,
        args=["tests.cli.test_check:unsatisfied_engin"],
    )
    assert result.exit_code == 1
    assert "❌ Missing providers found:" in result.output
    assert "int" in result.output


def test_check_complex_missing_dependencies():
    result = runner.invoke(
        app=cli,
        args=["tests.cli.test_check:complex_unsatisfied_engin"],
    )
    assert result.exit_code == 1
    assert "❌ Missing providers found:" in result.output
    assert "dict" in result.output


def test_check_invalid_app_path():
    result = runner.invoke(
        app=cli,
        args=["tests.cli.nonexistent:engin"],
    )
    assert result.exit_code == 1
    assert "Unable to find module" in result.output


def test_check_invalid_app_attribute():
    result = runner.invoke(
        app=cli,
        args=["tests.cli.test_check:nonexistent_engin"],
    )
    assert result.exit_code == 1
    assert "has no attribute" in result.output


def test_check_invalid_app_format():
    result = runner.invoke(
        app=cli,
        args=["invalid_format"],
    )
    assert result.exit_code == 1
    assert "Expected an argument of the form 'module:attribute'" in result.output


def test_check_not_engin_instance():
    result = runner.invoke(
        app=cli,
        args=["tests.cli.test_check:runner"],  # CliRunner is not an Engin
    )
    assert result.exit_code == 1
    assert "is not an Engin instance" in result.output
