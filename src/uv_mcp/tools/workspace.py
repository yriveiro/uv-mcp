"""Tools for inspecting uv workspaces."""

from typing import Any

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.tools.common import READ_ONLY, services


@app.tool(name="workspace_metadata", annotations=READ_ONLY)
def workspace_metadata(
    ctx: Context,
    project_path: str | None = None,
    script: str | None = None,
) -> dict[str, Any]:
    """View metadata about the current workspace.

    Args:
        project_path: Optional workspace working directory.
        script: Optional PEP 723 script to inspect instead.
        ctx: FastMCP request context.

    Returns:
        Workspace metadata.
    """
    command = ["workspace", "metadata", "--preview-features", "workspace-metadata"]
    if script:
        command.extend(["--script", script])
    return services(ctx).uv.run_uv_json(command, cwd=project_path)


@app.tool(name="workspace_list", annotations=READ_ONLY)
def workspace_list(
    ctx: Context,
    project_path: str | None = None,
    paths: bool = False,
    scripts: bool = False,
) -> list[str]:
    """List workspace members.

    Args:
        project_path: Optional workspace working directory.
        paths: Show member paths instead of names.
        scripts: Include standalone scripts with inline metadata.
        ctx: FastMCP request context.

    Returns:
        Workspace member names or paths.
    """
    command = ["workspace", "list"]
    if paths:
        command.append("--paths")
    if scripts:
        command.append("--scripts")
    output = services(ctx).uv.run_uv_command(command, cwd=project_path)
    return [line.strip() for line in output.splitlines() if line.strip()]


@app.tool(name="workspace_dir", annotations=READ_ONLY)
def workspace_dir(
    ctx: Context,
    project_path: str | None = None,
    package: str | None = None,
) -> str:
    """Display the path to a workspace member.

    Args:
        project_path: Optional workspace working directory.
        package: Optional workspace package name.
        ctx: FastMCP request context.

    Returns:
        Workspace member path.
    """
    command = ["workspace", "dir"]
    if package:
        command.extend(["--package", package])
    return services(ctx).uv.run_uv_command(command, cwd=project_path).strip()
