"""Tools for inspecting and updating the uv executable."""

import re

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.models import SelfUpdateResult, SelfVersionResult
from uv_mcp.tools.common import DESTRUCTIVE, READ_ONLY, services


def _version(output: str) -> str | None:
    """Extract a uv version from command output."""
    match = re.search(r"\buv\s+(\S+)", output)
    return match.group(1) if match else None


@app.tool(name="self_version", annotations=READ_ONLY)
def self_version(ctx: Context) -> SelfVersionResult:
    """Return the installed uv version.

    Args:
        ctx: FastMCP request context.

    Returns:
        Installed uv version.
    """
    output = services(ctx).uv.run_uv_command(["--version"])
    return SelfVersionResult(version=_version(output) or output.strip())


@app.tool(name="self_update", annotations=DESTRUCTIVE)
def self_update(ctx: Context, target_version: str | None = None) -> SelfUpdateResult:
    """Update the uv executable.

    Args:
        ctx: FastMCP request context.
        target_version: Optional version to install.

    Returns:
        Update result. Authentication tokens are not accepted or returned.
    """
    wrapper = services(ctx).uv
    previous = _version(wrapper.run_uv_command(["--version"]))
    command = ["self", "update"]
    if target_version:
        command.append(target_version)
    output = wrapper.run_uv_command(command)
    current = _version(wrapper.run_uv_command(["--version"]))
    return SelfUpdateResult(
        success=True,
        previous=previous,
        current=current,
        message=output.strip() or "uv updated successfully.",
    )
