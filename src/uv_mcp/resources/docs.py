"""Cached UV documentation resources under the ``uv:`` URI domain."""

from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ResourceError

from uv_mcp.app import app
from uv_mcp.context import services


@app.resource(
    "uv:docs://{section}",
    name="uv_docs_section",
    mime_type="application/json",
)
async def get_docs_section(ctx: Context, section: str) -> dict[str, Any]:
    """List commands or settings in a UV documentation section."""
    try:
        return await services(ctx).docs.get_section_overview(section)
    except (FileNotFoundError, ValueError) as e:
        raise ResourceError(str(e)) from e


@app.resource(
    "uv:docs://{section}/{command}",
    name="uv_docs_command",
    mime_type="application/json",
)
async def get_docs_command(ctx: Context, section: str, command: str) -> dict[str, Any]:
    """Return metadata and subsection links for a UV documentation entry."""
    try:
        return await services(ctx).docs.get_command_docs(section, command)
    except (FileNotFoundError, ValueError) as e:
        raise ResourceError(str(e)) from e


@app.resource(
    "uv:docs://{section}/{command}/{subsection}",
    name="uv_docs_subsection",
    mime_type="application/json",
)
async def get_docs_subsection(
    ctx: Context, section: str, command: str, subsection: str
) -> dict[str, Any]:
    """Return detailed content for a UV documentation subsection."""
    try:
        return await services(ctx).docs.get_subsection_docs(
            section, command, subsection
        )
    except (FileNotFoundError, ValueError) as e:
        raise ResourceError(str(e)) from e
