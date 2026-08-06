import importlib
from pathlib import Path

from typer.testing import CliRunner

from uv_mcp.cli import app

cli_app = importlib.import_module("uv_mcp.cli.app")

runner = CliRunner()


def test_serve_passes_venv_path(monkeypatch, tmp_path: Path) -> None:
    received: list[str | None] = []
    monkeypatch.setattr(cli_app, "_start_server", received.append)

    result = runner.invoke(app, ["serve", str(tmp_path)])

    assert result.exit_code == 0
    assert received == [str(tmp_path)]


def test_no_arguments_starts_server(monkeypatch) -> None:
    received: list[str | None] = []
    monkeypatch.setattr(
        cli_app,
        "_start_server",
        lambda venv_path=None: received.append(venv_path),
    )

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert received == [None]


def test_legacy_positional_venv_path_is_rejected(tmp_path: Path) -> None:
    result = runner.invoke(app, [str(tmp_path)])

    assert result.exit_code == 2
