"""Tools for managing globally installed uv tools."""

import re

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.models import ToolInfo, ToolListResult, ToolOperationResult
from uv_mcp.tools.common import DESTRUCTIVE, IDEMPOTENT, READ_ONLY, services
from uv_mcp.uv_wrapper import spec

_TOOL_HEADER = re.compile(r"^(?P<name>\S+)\s+v(?P<version>\S+)$")


def parse_tool_list(output: str) -> ToolListResult:
    """Parse the human-readable output of ``uv tool list``.

    Args:
        output: Output from uv.

    Returns:
        Parsed tool records.
    """
    tools: list[ToolInfo] = []
    for line in output.splitlines():
        header = _TOOL_HEADER.match(line.strip())
        if header:
            tools.append(
                ToolInfo(
                    name=header["name"],
                    version=header["version"],
                    executables=[],
                )
            )
        elif line.strip().startswith("-") and tools:
            executable = line.strip()[1:].strip()
            if executable:
                tools[-1].executables.append(executable)
    return ToolListResult(tools=tools)


@app.tool(name="tool_install")
def tool_install(
    ctx: Context,
    package: str,
    version: str | None = None,
    python: str | None = None,
) -> ToolOperationResult:
    """Install a package as a globally available uv tool.

    Args:
        package: Package name.
        version: Optional exact version.
        python: Optional Python interpreter request.
        ctx: FastMCP request context.

    Returns:
        Installation result.
    """
    command = ["tool", "install", spec(package, version)]
    if python:
        command.extend(["--python", python])
    output = services(ctx).uv.run_uv_command(command)
    return ToolOperationResult(
        name=package,
        success=True,
        message=output.strip() or "Tool installed successfully.",
    )


@app.tool(name="tool_upgrade")
def tool_upgrade(ctx: Context, name: str | None = None) -> ToolOperationResult:
    """Upgrade one uv tool, or all tools when no name is given.

    Args:
        name: Optional tool name.
        ctx: FastMCP request context.

    Returns:
        Upgrade result.
    """
    command = ["tool", "upgrade"]
    if name:
        command.append(name)
    output = services(ctx).uv.run_uv_command(command)
    return ToolOperationResult(
        name=name or "all",
        success=True,
        message=output.strip() or "Tools upgraded successfully.",
    )


@app.tool(name="tool_list", annotations=READ_ONLY)
def tool_list(ctx: Context) -> ToolListResult:
    """List globally installed uv tools.

    Args:
        ctx: FastMCP request context.

    Returns:
        Installed tool records.
    """
    return parse_tool_list(services(ctx).uv.run_uv_command(["tool", "list"]))


@app.tool(name="tool_uninstall", annotations=DESTRUCTIVE)
def tool_uninstall(ctx: Context, name: str) -> ToolOperationResult:
    """Uninstall a globally installed uv tool.

    Args:
        name: Tool name.
        ctx: FastMCP request context.

    Returns:
        Uninstallation result.
    """
    output = services(ctx).uv.run_uv_command(["tool", "uninstall", name])
    return ToolOperationResult(
        name=name,
        success=True,
        message=output.strip() or "Tool uninstalled successfully.",
    )


@app.tool(name="tool_dir", annotations=READ_ONLY)
def tool_dir(ctx: Context, bin: bool = False) -> str:
    """Show the uv tools directory."""
    command = ["tool", "dir"]
    if bin:
        command.append("--bin")
    return services(ctx).uv.run_uv_command(command).strip()


@app.tool(name="tool_update_shell", annotations=IDEMPOTENT)
def tool_update_shell(ctx: Context) -> str:
    """Ensure the uv tool executable directory is on ``PATH``."""
    return services(ctx).uv.run_uv_command(["tool", "update-shell"])
