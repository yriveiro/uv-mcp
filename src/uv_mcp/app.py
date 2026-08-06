"""FastMCP application assembly: instance and lifespan.

The shared :data:`app` instance is imported by every module in
:mod:`uv_mcp.tools` and :mod:`uv_mcp.resources`, which register their
components at import time. Importing :mod:`uv_mcp.tools` and
:mod:`uv_mcp.resources` (via :mod:`uv_mcp.server`) triggers registration.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP

from uv_mcp.context import ServerContext
from uv_mcp.docs import CacheManager
from uv_mcp.settings import Settings, configure_logging
from uv_mcp.uv_wrapper import UVWrapper


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[ServerContext]:
    """Build the shared services for the lifetime of the server.

    Args:
        _server: The FastMCP server instance (unused).

    Yields:
        A :class:`ServerContext` exposing the uv wrapper and documentation
        cache to tools and resources.
    """
    settings = Settings()
    configure_logging(settings)
    docs = CacheManager(
        cache_dir=Path(settings.cache_dir) if settings.cache_dir else None
    )
    await docs.initialize()
    yield ServerContext(
        uv=UVWrapper(
            settings.venv_path,
            settings.uv_binary,
            settings.command_timeout,
        ),
        docs=docs,
    )


app = FastMCP(
    "uv-mcp",
    instructions=(
        "Manage Python projects and environments with uv. "
        "Inspect installed or outdated packages via the resources, "
        "then use the tools to run commands, add or remove "
        "dependencies, sync and lock the project, manage packages "
        "with pip, handle Python versions and uv tools, or browse "
        "the cached UV documentation. Audit projects and installed tools "
        "for known vulnerabilities and adverse package statuses."
    ),
    version="0.2.0",
    lifespan=lifespan,
)
