import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.exceptions import Exit

from engin import Engin
from engin._cli._common import get_engin_instance

instance_a = Engin()
instance_b = Engin()


def test_get_engin_instance_with_default_from_pyproject():
    pyproject_content = """
[tool.engin]
default-instance = "tests.cli.test_get_engin_instance:instance_a"
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        with patch("pathlib.Path.cwd", return_value=temp_path):
            _, _, found_instance = get_engin_instance()
            assert found_instance == instance_a


def test_get_engin_instance_when_app_overrides_default():
    pyproject_content = """
[tool.engin]
default-instance = "tests.cli.test_check:instance_a"
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        with patch("pathlib.Path.cwd", return_value=temp_path):
            _, _, found_instance = get_engin_instance(
                "tests.cli.test_get_engin_instance:instance_b"
            )
            assert found_instance == instance_b


def test_get_engin_instance_with_no_default_no_app():
    pyproject_content = """
[project]
name = "test"
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        with (
            patch("pathlib.Path.cwd", return_value=temp_path),
            pytest.raises(Exit),
        ):
            get_engin_instance()


def test_get_engin_instance_with_no_default_and_no_pyproject_toml():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        with (
            patch("pathlib.Path.cwd", return_value=temp_path),
            pytest.raises(Exit),
        ):
            get_engin_instance()


def test_check_with_no_default_and_invalid_toml():
    pyproject_content = """
[]]
name -- test
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        with (
            patch("pathlib.Path.cwd", return_value=temp_path),
            pytest.raises(Exit),
        ):
            get_engin_instance()


def test_check_with_no_default_and_invalid_value_type():
    pyproject_content = """
[tool.engin]
default-instance = 3.1
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pyproject_path = temp_path / "pyproject.toml"
        pyproject_path.write_text(pyproject_content)

        with (
            patch("pathlib.Path.cwd", return_value=temp_path),
            pytest.raises(Exit),
        ):
            get_engin_instance()
