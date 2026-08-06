from uv_mcp.settings import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("UV_MCP_VENV_PATH", "/tmp/project/.venv")
    monkeypatch.setenv("UV_MCP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("UV_MCP_UV_BINARY", "/opt/uv")
    monkeypatch.setenv("UV_MCP_COMMAND_TIMEOUT", "12.5")
    monkeypatch.setenv("UV_MCP_CACHE_DIR", "/tmp/uv-mcp-cache")

    settings = Settings()

    assert settings.venv_path == "/tmp/project/.venv"
    assert settings.log_level == "DEBUG"
    assert settings.uv_binary == "/opt/uv"
    assert settings.command_timeout == 12.5
    assert settings.cache_dir == "/tmp/uv-mcp-cache"


def test_settings_defaults(monkeypatch) -> None:
    for name in (
        "UV_MCP_VENV_PATH",
        "UV_MCP_LOG_LEVEL",
        "UV_MCP_UV_BINARY",
        "UV_MCP_COMMAND_TIMEOUT",
        "UV_MCP_CACHE_DIR",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings()

    assert settings.venv_path is None
    assert settings.log_level == "INFO"
    assert settings.uv_binary is None
    assert settings.command_timeout is None
    assert settings.cache_dir is None
