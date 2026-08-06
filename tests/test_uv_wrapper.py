from unittest.mock import Mock, patch

import pytest

from uv_mcp.models import Package
from uv_mcp.uv_wrapper import UVCommandError, UVWrapper, spec


def test_spec() -> None:
    assert spec("requests") == "requests"
    assert spec("requests", "2.0") == "requests==2.0"


@patch("uv_mcp.uv_wrapper.uv.find_uv_bin", return_value="/usr/bin/uv")
@patch("uv_mcp.uv_wrapper.subprocess.run")
def test_run_uv_command(mock_run: Mock, mock_find_uv_bin: Mock) -> None:
    mock_run.return_value = Mock(returncode=0, stdout="ok", stderr="")

    result = UVWrapper().run_uv_command(["--version"])

    assert result == "ok"
    mock_find_uv_bin.assert_called_once_with()
    assert mock_run.call_args.args[0] == ["/usr/bin/uv", "--version"]


@patch("uv_mcp.uv_wrapper.uv.find_uv_bin", return_value="/usr/bin/uv")
@patch("uv_mcp.uv_wrapper.subprocess.run")
def test_run_uv_command_raises_on_failure(
    mock_run: Mock, mock_find_uv_bin: Mock
) -> None:
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="bad command")

    with pytest.raises(UVCommandError, match="bad command"):
        UVWrapper().run_uv_command(["bad"])


@patch("uv_mcp.uv_wrapper.uv.find_uv_bin", return_value="/usr/bin/uv")
@patch("uv_mcp.uv_wrapper.subprocess.run")
def test_run_uv_command_can_return_output_on_expected_failure(
    mock_run: Mock, mock_find_uv_bin: Mock
) -> None:
    mock_run.return_value = Mock(
        returncode=1, stdout='{"findings": []}', stderr="findings"
    )

    result = UVWrapper().run_uv_command(["audit"], check=False)

    assert result == '{"findings": []}'


@patch("uv_mcp.uv_wrapper.uv.find_uv_bin", return_value="/usr/bin/uv")
@patch("uv_mcp.uv_wrapper.subprocess.run")
def test_run_uv_json_can_parse_output_on_expected_failure(
    mock_run: Mock, mock_find_uv_bin: Mock
) -> None:
    mock_run.return_value = Mock(
        returncode=1, stdout='{"findings": []}', stderr="findings"
    )

    assert UVWrapper().run_uv_json(["audit"], check=False) == {"findings": []}


@patch.object(
    UVWrapper, "run_uv_command", return_value='[{"name": "uv", "version": "1"}]'
)
def test_list_packages_in_venv_targets_interpreter(mock_run: Mock) -> None:
    packages = UVWrapper().list_packages_in_venv("/tmp/project/.venv")

    assert packages == [Package(name="uv", version="1")]
    mock_run.assert_called_once_with(
        [
            "pip",
            "list",
            "--python",
            "/tmp/project/.venv/bin/python",
            "--format",
            "json",
        ]
    )


@patch.object(UVWrapper, "run_uv_command", return_value="installed")
def test_install_package_can_target_venv(mock_run: Mock) -> None:
    UVWrapper().install_package("requests", "2.0", "/tmp/project/.venv")

    mock_run.assert_called_once_with(
        [
            "pip",
            "install",
            "--python",
            "/tmp/project/.venv/bin/python",
            "requests==2.0",
        ]
    )
