import asyncio
import json

from fastmcp import Client

from uv_mcp.docs import CacheManager
from uv_mcp.server import mcp


def _seed_docs_cache(cache_dir) -> None:
    cache_dir.mkdir()
    (cache_dir / "version.json").write_text('{"version": "test"}')
    (cache_dir / "cli.json").write_text(
        json.dumps(
            {
                "elements": [
                    {
                        "name": "uv run",
                        "description": "Run a command or script.",
                        "documentation": [
                            {"title": "Examples", "content": ["Run Python."]}
                        ],
                    }
                ]
            }
        )
    )
    for section in ("settings", "resolver"):
        (cache_dir / f"{section}.json").write_text('{"elements": []}')


def test_server_registers_expected_components(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "docs"
    _seed_docs_cache(cache_dir)
    monkeypatch.setenv("UV_MCP_CACHE_DIR", str(cache_dir))

    async def inspect_server() -> tuple[list[str], list[str], list[str], list[str]]:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            prompts = await client.list_prompts()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            return (
                sorted(tool.name for tool in tools),
                sorted(prompt.name for prompt in prompts),
                sorted(str(resource.uri) for resource in resources),
                sorted(str(template.uriTemplate) for template in templates),
            )

    tools, prompts, resources, templates = asyncio.run(inspect_server())

    assert "compare_environments" in tools
    assert "create_virtualenv" in tools
    assert "audit" in tools
    assert "tool_audit" in tools
    assert "summarize_docs" in prompts
    assert "python:requirements://{file_path*}" in templates
    assert "uv:docs://{section}" in templates
    assert "uv:docs://{section}/{command}" in templates
    assert "uv:docs://{section}/{command}/{subsection}" in templates
    assert "python:packages://installed" in resources


def test_server_reads_and_searches_docs(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "docs"
    _seed_docs_cache(cache_dir)
    monkeypatch.setenv("UV_MCP_CACHE_DIR", str(cache_dir))

    async def inspect_server() -> None:
        async with Client(mcp) as client:
            section = await client.read_resource("uv:docs://cli")
            command = await client.read_resource("uv:docs://cli/uv-run")
            subsection = await client.read_resource("uv:docs://cli/uv-run/examples")
            results = await client.call_tool("search_documentation", {"query": "run"})
            assert "uv:docs://cli/uv-run" in str(section)
            assert "Examples" in str(command)
            assert "Run Python." in str(subsection)
            assert "uv:docs://cli/uv-run" in str(results)

    asyncio.run(inspect_server())


def test_update_cache_reports_current_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "docs"
    _seed_docs_cache(cache_dir)
    monkeypatch.setenv("UV_MCP_CACHE_DIR", str(cache_dir))

    async def current_version(self) -> dict[str, str]:
        return {"version": "test"}

    monkeypatch.setattr(CacheManager, "fetch_current_version", current_version)

    async def inspect_server() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("update_cache", {"force": False})
            assert "up to date" in str(result)

    asyncio.run(inspect_server())


def test_summarize_docs_prompt_includes_selected_section(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "docs"
    _seed_docs_cache(cache_dir)
    monkeypatch.setenv("UV_MCP_CACHE_DIR", str(cache_dir))

    async def inspect_server() -> None:
        async with Client(mcp) as client:
            result = await client.get_prompt("summarize_docs", {"section": "cli"})
            assert "uv run" in str(result)
            assert "uv:docs:// resources" in str(result)

    asyncio.run(inspect_server())
