import pytest

from uv_mcp.docs import (
    CacheManager,
    parse_cli_documentation,
    parse_resolver_documentation,
    parse_settings_documentation,
)

CLI_HTML = """
<div class="md-content">
  <h2>uv run</h2>
  <p>Run a command or script.</p>
  <h3>Examples</h3>
  <p>Run a script in the project environment.</p>
  <dl><dt>--no-sync</dt><dd>Skip syncing.</dd></dl>
  <h2>uv cache</h2>
  <p>Manage the cache.</p>
</div>
"""

SETTINGS_HTML = """
<div class="md-content">
  <h2>UV_INDEX_URL</h2>
  <p>The package index URL.</p>
  <div class="highlight"><pre>https://example.test/simple</pre></div>
</div>
"""

RESOLVER_HTML = """
<div class="md-content">
  <h2>Resolution</h2>
  <p>How packages are resolved.</p>
  <div class="admonition"><p>Resolver note.</p></div>
  <ul><li>Choose compatible versions.</li></ul>
</div>
"""


def test_documentation_parsers_extract_structured_content() -> None:
    cli = parse_cli_documentation(CLI_HTML)
    assert cli["elements"][0]["name"] == "uv run"
    documentation = cli["elements"][0]["documentation"]
    examples = next(
        section for section in documentation if section["title"] == "Examples"
    )
    options = next(
        section for section in documentation if section["title"] == "Options"
    )
    assert "Run a script in the project environment." in examples["content"]
    assert "--no-sync: Skip syncing." in options["content"]

    settings = parse_settings_documentation(SETTINGS_HTML)
    assert settings["elements"][0]["name"] == "UV_INDEX_URL"
    assert (
        "Example:\nhttps://example.test/simple"
        in settings["elements"][0]["documentation"][0]["content"]
    )

    resolver = parse_resolver_documentation(RESOLVER_HTML)
    assert resolver["elements"][0]["description"] == (
        "How packages are resolved. Resolver note. - Choose compatible versions."
    )


@pytest.mark.anyio
async def test_cache_manager_round_trip_and_search(tmp_path) -> None:
    manager = CacheManager(tmp_path)
    await manager.update_version({"version": "1.0"})
    await manager.update_section(
        "cli",
        {
            "elements": [
                {
                    "name": "uv run",
                    "description": "Run commands in the project environment.",
                    "documentation": [
                        {"title": "Examples", "content": ["Run Python."]}
                    ],
                }
            ]
        },
    )

    assert await manager.get_cached_version() == {"version": "1.0"}
    assert (await manager.get_cached_section("cli"))["elements"][0]["name"] == "uv run"
    results = await manager.search("run")
    assert results[0]["path"] == "uv:docs://cli/uv-run"

    await manager.clear_cache()
    assert not (tmp_path / "version.json").exists()


@pytest.mark.anyio
async def test_cache_initialize_skips_existing_cache(tmp_path, monkeypatch) -> None:
    manager = CacheManager(tmp_path)
    await manager.update_version({"version": "1.0"})

    async def fail() -> dict[str, str]:
        raise AssertionError("existing cache should not be fetched")

    monkeypatch.setattr(manager, "fetch_current_version", fail)
    await manager.initialize()


@pytest.mark.anyio
async def test_cache_validity(tmp_path, monkeypatch) -> None:
    manager = CacheManager(tmp_path)
    await manager.update_version({"version": "1.0"})

    async def current() -> dict[str, str]:
        return {"version": "1.0"}

    monkeypatch.setattr(manager, "fetch_current_version", current)
    assert await manager.is_cache_valid()
