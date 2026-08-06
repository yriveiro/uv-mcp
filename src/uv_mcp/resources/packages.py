"""Package and environment resources under the ``python:`` URI domain."""

from typing import Any

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.context import services


@app.resource(
    "python:packages://installed",
    name="installed_packages",
    mime_type="application/json",
)
def get_installed_packages(ctx: Context) -> list[dict[str, Any]]:
    """List of all installed packages and versions."""
    return [
        package.model_dump(mode="json")
        for package in services(ctx).uv.list_installed_packages()
    ]


@app.resource(
    "python:packages://outdated",
    name="outdated_packages",
    mime_type="application/json",
)
def get_outdated_packages(ctx: Context) -> list[dict[str, Any]]:
    """List of installed packages with newer versions available."""
    return [
        package.model_dump(mode="json")
        for package in services(ctx).uv.get_outdated_packages()
    ]


@app.resource(
    "python:packages://{package_name}/info",
    name="package_info",
    mime_type="application/json",
)
def get_package_info_resource(ctx: Context, package_name: str) -> str:
    """Detailed information about a specific package."""
    return services(ctx).uv.get_package_info(package_name)
