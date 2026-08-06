"""Server entry point.

Imports :mod:`uv_mcp.tools` and :mod:`uv_mcp.resources` to register every
component on the shared
:data:`uv_mcp.app.app` instance, then exposes that instance as ``mcp`` for
clients and the ``python -m uv_mcp.server`` entry point.
"""

import uv_mcp.resources  # noqa: F401  (importing registers all resources)
import uv_mcp.tools  # noqa: F401  (importing registers all tools)
from uv_mcp.app import app as mcp
from uv_mcp.settings import Settings, configure_logging

__all__ = ["mcp"]


if __name__ == "__main__":
    configure_logging(Settings())
    mcp.run()
