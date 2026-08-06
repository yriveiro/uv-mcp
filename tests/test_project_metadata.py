import tomllib
from pathlib import Path


def test_only_hyphenated_cli_script_is_exposed() -> None:
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())

    assert project["project"]["scripts"] == {"uv-mcp": "uv_mcp.cli:run"}
