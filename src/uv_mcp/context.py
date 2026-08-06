"""Shared runtime state exposed to tools and resources."""

from dataclasses import dataclass
from typing import cast

from fastmcp import Context

from uv_mcp.docs import CacheManager
from uv_mcp.uv_wrapper import UVWrapper


@dataclass(slots=True)
class ServerContext:
    """Per-server shared services created by the lifespan.

    Attributes:
        uv: Wrapper around the uv CLI.
        docs: Manager for the UV documentation cache.
    """

    uv: UVWrapper
    docs: CacheManager


def services(ctx: Context) -> ServerContext:
    """Return the typed server services from a FastMCP context.

    Args:
        ctx: FastMCP request context.

    Returns:
        The shared services created by the server lifespan.
    """
    return cast(ServerContext, ctx.lifespan_context)
