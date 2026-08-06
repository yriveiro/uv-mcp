"""Tools for uv's pip-compatible workflows."""

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.models import Package
from uv_mcp.tools.common import DESTRUCTIVE, READ_ONLY, services


@app.tool(name="pip")
def pip_command(ctx: Context, command: list[str]) -> str:
    """Run an arbitrary uv pip command.

    Args:
        command: Arguments passed after ``uv pip``.
        ctx: FastMCP request context.

    Returns:
        Command output.
    """
    return services(ctx).uv.run_uv_command(["pip", *command])


@app.tool(name="pip_install")
def pip_install(
    ctx: Context,
    package_name: str,
    version: str | None = None,
    venv_path: str | None = None,
) -> str:
    """Install a package using uv pip.

    Args:
        package_name: Package name.
        version: Optional exact version.
        venv_path: Optional target virtual environment.
        ctx: FastMCP request context.

    Returns:
        Command output.
    """
    return services(ctx).uv.install_package(package_name, version, venv_path)


@app.tool(name="pip_uninstall", annotations=DESTRUCTIVE)
def pip_uninstall(ctx: Context, package_name: str, venv_path: str | None = None) -> str:
    """Uninstall a package using uv pip.

    Args:
        package_name: Package name.
        venv_path: Optional target virtual environment.
        ctx: FastMCP request context.

    Returns:
        Command output.
    """
    return services(ctx).uv.uninstall_package(package_name, venv_path)


@app.tool(name="pip_list", annotations=READ_ONLY)
def pip_list(ctx: Context, venv_path: str | None = None) -> list[Package]:
    """List packages installed by uv pip.

    Args:
        venv_path: Optional target virtual environment.
        ctx: FastMCP request context.

    Returns:
        Installed package records.
    """
    return services(ctx).uv.list_installed_packages(venv_path)


@app.tool(name="pip_compile")
def pip_compile(
    ctx: Context,
    input_file: str,
    output_file: str | None = None,
    python: str | None = None,
) -> str:
    """Compile a requirements input file into a pinned requirements file.

    Args:
        input_file: Input requirements file.
        output_file: Optional output file.
        python: Optional Python request used for resolution.
        ctx: FastMCP request context.

    Returns:
        Compiler output.
    """
    command = ["pip", "compile", input_file]
    if output_file:
        command.extend(["--output-file", output_file])
    if python:
        command.extend(["--python", python])
    return services(ctx).uv.run_uv_command(command)


@app.tool(name="pip_sync", annotations=DESTRUCTIVE)
def pip_sync(ctx: Context, requirements_file: str) -> str:
    """Synchronize an environment to a requirements file.

    Args:
        requirements_file: Requirements file to install.
        ctx: FastMCP request context.

    Returns:
        Synchronization output.
    """
    return services(ctx).uv.run_uv_command(["pip", "sync", requirements_file])


@app.tool(name="pip_freeze", annotations=READ_ONLY)
def pip_freeze(ctx: Context, venv_path: str | None = None) -> str:
    """Freeze installed packages into requirements syntax.

    Args:
        venv_path: Optional target virtual environment.
        ctx: FastMCP request context.

    Returns:
        Frozen requirements text.
    """
    return services(ctx).uv.run_uv_command(
        ["pip", "freeze", *services(ctx).uv._python_flag(venv_path)]
    )
