"""Tools for inspecting and cleaning uv's cache."""

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.models import CacheInfo, CacheOperationResult
from uv_mcp.tools.common import DESTRUCTIVE, READ_ONLY, services


@app.tool(name="cache_clean", annotations=DESTRUCTIVE)
def cache_clean(ctx: Context, package: str | None = None) -> CacheOperationResult:
    """Clear all cache entries, or entries associated with a package.

    Args:
        package: Optional package to target.
        ctx: FastMCP request context.

    Returns:
        Cleanup result.
    """
    command = ["cache", "clean"]
    if package:
        command.append(package)
    output = services(ctx).uv.run_uv_command(command)
    return CacheOperationResult(
        success=True,
        package=package,
        message=output.strip() or "Cache cleaned successfully.",
    )


@app.tool(name="cache_prune", annotations=DESTRUCTIVE)
def cache_prune(ctx: Context, ci: bool = False) -> CacheOperationResult:
    """Prune dangling cache entries and environments.

    Args:
        ci: Use CI-specific pruning behavior.
        ctx: FastMCP request context.

    Returns:
        Pruning result.
    """
    command = ["cache", "prune"]
    if ci:
        command.append("--ci")
    output = services(ctx).uv.run_uv_command(command)
    return CacheOperationResult(
        success=True,
        message=output.strip() or "Cache pruned successfully.",
    )


@app.tool(name="cache_dir", annotations=READ_ONLY)
def cache_dir(ctx: Context) -> CacheInfo:
    """Return uv's cache directory.

    Args:
        ctx: FastMCP request context.

    Returns:
        Cache directory information.
    """
    path = services(ctx).uv.run_uv_command(["cache", "dir"]).strip()
    return CacheInfo(directory=path)


@app.tool(name="cache_size", annotations=READ_ONLY)
def cache_size(ctx: Context) -> CacheInfo:
    """Return uv's cache directory and its size in bytes.

    Args:
        ctx: FastMCP request context.

    Returns:
        Cache size information.
    """
    wrapper = services(ctx).uv
    directory = wrapper.run_uv_command(["cache", "dir"]).strip()
    size = int(wrapper.run_uv_command(["cache", "size"]).strip())
    return CacheInfo(directory=directory, size_bytes=size)
