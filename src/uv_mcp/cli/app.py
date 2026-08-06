#!/usr/bin/env python3
"""Typer application for uv-mcp."""

import os
from typing import Annotated

import typer

from uv_mcp.cli.display import error
from uv_mcp.cli.skills import skill_app
from uv_mcp.settings import Settings, configure_logging

app = typer.Typer(
    help="MCP server for interacting with Python installations via uv.",
    no_args_is_help=False,
)
app.add_typer(skill_app, name="skill")


def _start_server(venv_path: str | None = None) -> None:
    """Configure and run the FastMCP server."""
    settings = Settings() if venv_path is None else Settings(venv_path=venv_path)
    configure_logging(settings)
    if settings.venv_path:
        os.environ["UV_MCP_VENV_PATH"] = settings.venv_path

    try:
        from uv_mcp.server import mcp

        mcp.run()
    except ImportError as e:
        error(f"Error importing server module: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        error(f"Error running server: {e}")
        raise typer.Exit(code=1) from e


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run the MCP server when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        _start_server()


@app.command()
def serve(
    venv_path: Annotated[
        str | None,
        typer.Argument(help="Path to the virtual environment"),
    ] = None,
) -> None:
    """Run the MCP server over stdio."""
    _start_server(venv_path)


def run() -> None:
    """Run the Typer application."""
    app()
