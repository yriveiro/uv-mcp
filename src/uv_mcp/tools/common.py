"""Shared helpers for FastMCP tool modules."""

from mcp.types import ToolAnnotations

from uv_mcp.context import services

__all__ = ["DESTRUCTIVE", "IDEMPOTENT", "READ_ONLY", "services"]

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    openWorldHint=False,
)
IDEMPOTENT = ToolAnnotations(idempotentHint=True)
DESTRUCTIVE = ToolAnnotations(destructiveHint=True)
