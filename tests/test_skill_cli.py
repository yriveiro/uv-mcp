from pathlib import Path

import pytest
from typer.testing import CliRunner

from uv_mcp.cli import app
from uv_mcp.cli.skills import bundled_skill_names, install_skill

runner = CliRunner()


def test_bundled_skill_names_include_uv() -> None:
    assert "uv" in bundled_skill_names()


def test_install_skill_copies_to_agents_layout(tmp_path: Path) -> None:
    destination, files = install_skill("uv", tmp_path)

    assert destination == tmp_path / ".agents" / "skills" / "uv"
    assert (destination / "SKILL.md").is_file()
    assert any(path.name == "MCP-TOOLS.md" for path in destination.rglob("*"))
    assert files == sorted(
        str(path.relative_to(destination))
        for path in destination.rglob("*")
        if path.is_file()
    )


def test_install_skill_requires_force_for_existing(tmp_path: Path) -> None:
    install_skill("uv", tmp_path)

    with pytest.raises(ValueError, match="already installed"):
        install_skill("uv", tmp_path)

    install_skill("uv", tmp_path, force=True)


def test_install_unknown_skill_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown skill"):
        install_skill("nonexistent", tmp_path)


def test_skill_install_via_cli(tmp_path: Path) -> None:
    result = runner.invoke(app, ["skill", "install", "uv", "--target", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / ".agents" / "skills" / "uv" / "SKILL.md").is_file()


def test_skill_install_unknown_returns_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["skill", "install", "nonexistent", "--target", str(tmp_path)],
    )

    assert result.exit_code == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["--help"],
        ["skill", "--help"],
        ["skill", "install", "--help"],
    ],
)
def test_cli_help_contract(arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)

    assert result.exit_code == 0
