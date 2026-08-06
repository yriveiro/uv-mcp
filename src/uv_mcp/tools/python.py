"""Tools for managing Python installations through uv."""

import json

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.models import (
    PythonDirResult,
    PythonFindResult,
    PythonInfo,
    PythonListResult,
    PythonOperationResult,
)
from uv_mcp.tools.common import DESTRUCTIVE, IDEMPOTENT, READ_ONLY, services


def parse_python_list(output: str) -> PythonListResult:
    """Parse ``uv python list --output-format json`` output.

    Args:
        output: JSON output from uv.

    Returns:
        Parsed Python installations.
    """
    records = json.loads(output)
    return PythonListResult(
        pythons=[
            PythonInfo(
                key=record.get("key", ""),
                version=record.get("version", ""),
                path=record.get("path"),
                implementation=record.get("implementation", ""),
                arch=record.get("arch", ""),
                os=record.get("os", ""),
                managed=record.get("managed", False),
            )
            for record in records
        ]
    )


def _operation_result(version: str, output: str) -> PythonOperationResult:
    """Create a successful Python operation result from uv output."""
    path = output.strip() or None
    return PythonOperationResult(
        version=version,
        success=True,
        message=output.strip() or "Operation completed successfully.",
        path=path,
    )


@app.tool(name="python_list", annotations=READ_ONLY)
def python_list(ctx: Context) -> PythonListResult:
    """List Python installations known to uv.

    Args:
        ctx: FastMCP request context.

    Returns:
        Installed and available Python records.
    """
    output = services(ctx).uv.run_uv_command(
        ["python", "list", "--output-format", "json"]
    )
    return parse_python_list(output)


@app.tool(name="python_install")
def python_install(ctx: Context, version: str) -> PythonOperationResult:
    """Install a managed Python version.

    Args:
        version: Python version request.
        ctx: FastMCP request context.

    Returns:
        Installation result.
    """
    output = services(ctx).uv.run_uv_command(["python", "install", version])
    return _operation_result(version, output)


@app.tool(name="python_pin")
def python_pin(
    ctx: Context, version: str, project_path: str | None = None
) -> PythonOperationResult:
    """Pin a Python version in a project.

    Args:
        version: Python version request.
        project_path: Optional project directory.
        ctx: FastMCP request context.

    Returns:
        Pinning result.
    """
    output = services(ctx).uv.run_uv_command(
        ["python", "pin", version], cwd=project_path
    )
    return _operation_result(version, output)


@app.tool(name="python_find", annotations=READ_ONLY)
def python_find(ctx: Context, request: str | None = None) -> PythonFindResult:
    """Find the path of a Python interpreter.

    Args:
        request: Optional Python version request.
        ctx: FastMCP request context.

    Returns:
        Resolved interpreter path.
    """
    command = ["python", "find"]
    if request:
        command.append(request)
    path = services(ctx).uv.run_uv_command(command).strip()
    return PythonFindResult(request=request, path=path)


@app.tool(name="python_upgrade")
def python_upgrade(ctx: Context, version: str) -> PythonOperationResult:
    """Reinstall a managed Python version.

    Args:
        version: Python version request.
        ctx: FastMCP request context.

    Returns:
        Upgrade result.
    """
    output = services(ctx).uv.run_uv_command(
        ["python", "install", "--reinstall", version]
    )
    return _operation_result(version, output)


@app.tool(name="python_uninstall", annotations=DESTRUCTIVE)
def python_uninstall(ctx: Context, version: str) -> PythonOperationResult:
    """Uninstall a managed Python version.

    Args:
        version: Python version request.
        ctx: FastMCP request context.

    Returns:
        Uninstallation result.
    """
    output = services(ctx).uv.run_uv_command(["python", "uninstall", version])
    return _operation_result(version, output)


@app.tool(name="python_dir", annotations=READ_ONLY)
def python_dir(ctx: Context, which: str = "default") -> PythonDirResult:
    """Show a uv-managed Python directory.

    Args:
        which: ``default`` or ``bin``.
        ctx: FastMCP request context.

    Returns:
        Directory result.
    """
    flags = {"default": [], "bin": ["--bin"]}
    try:
        command = ["python", "dir", *flags[which]]
    except KeyError as e:
        raise ValueError("which must be 'default' or 'bin'") from e
    path = services(ctx).uv.run_uv_command(command).strip()
    return PythonDirResult(which=which, path=path)


@app.tool(name="python_update_shell", annotations=IDEMPOTENT)
def python_update_shell(ctx: Context) -> str:
    """Ensure the uv-managed Python executable directory is on ``PATH``."""
    return services(ctx).uv.run_uv_command(["python", "update-shell"])
