"""Requirements-file resources under the ``python:`` URI domain."""

from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ResourceError

from uv_mcp.app import app
from uv_mcp.requirements import RequirementsError, parse_requirements_file


@app.resource(
    "python:requirements://{file_path*}",
    name="requirements_file",
    mime_type="application/json",
)
def get_requirements_resource(ctx: Context, file_path: str) -> dict[str, Any]:
    """Parsed contents of a requirements.txt or pyproject.toml file."""
    try:
        return parse_requirements_file(file_path).model_dump(mode="json")
    except RequirementsError as e:
        raise ResourceError(str(e)) from e
