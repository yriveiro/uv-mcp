"""Project-oriented uv tools."""

import re
import tomllib
from pathlib import Path

from fastmcp import Context
from fastmcp.exceptions import ToolError

from uv_mcp.app import app
from uv_mcp.models import (
    BuildResult,
    BumpResult,
    ExportResult,
    ManifestResult,
    ProjectVersion,
    PublishResult,
)
from uv_mcp.tools.common import DESTRUCTIVE, IDEMPOTENT, READ_ONLY, services


@app.tool(name="run")
def run_command(command: list[str], ctx: Context) -> str:
    """Run a command or script in the project environment.

    Args:
        command: Command and arguments to pass to ``uv run``.
        ctx: FastMCP request context.

    Returns:
        Command output.
    """
    return services(ctx).uv.run_uv_command(["run", *command])


@app.tool(name="init")
def init_project(
    ctx: Context,
    name: str | None = None,
    python_version: str | None = None,
    path: str | None = None,
    template: str = "app",
) -> str:
    """Create a new project.

    Args:
        name: Optional project name.
        python_version: Optional Python version request.
        path: Optional target path.
        template: ``app`` or ``lib``.
        ctx: FastMCP request context.

    Returns:
        uv's initialization output.
    """
    command = ["init"]
    if name:
        command.extend(["--name", name])
    if python_version:
        command.extend(["--python", python_version])
    if template == "app":
        command.append("--app")
    elif template == "lib":
        command.append("--lib")
    else:
        raise ValueError("template must be 'app' or 'lib'")
    if path:
        command.append(path)
    return services(ctx).uv.run_uv_command(command)


@app.tool(name="add")
def add_dependency(ctx: Context, package_name: str, version: str | None = None) -> str:
    """Add a dependency to the current project.

    Args:
        package_name: Package name.
        version: Optional exact version.
        ctx: FastMCP request context.

    Returns:
        uv's command output.
    """
    return services(ctx).uv.add_dependency(package_name, version)


@app.tool(name="remove", annotations=DESTRUCTIVE)
def remove_dependency(ctx: Context, package_name: str) -> str:
    """Remove a dependency from the current project.

    Args:
        package_name: Package name.
        ctx: FastMCP request context.

    Returns:
        uv's command output.
    """
    return services(ctx).uv.remove_dependency(package_name)


@app.tool(name="sync", annotations=IDEMPOTENT)
def sync_dependencies(
    ctx: Context,
    dry_run: bool = False,
    upgrade: bool = False,
    locked: bool = False,
) -> str:
    """Synchronize the project environment.

    Args:
        dry_run: Show changes without applying them.
        upgrade: Upgrade dependencies where possible.
        locked: Require the lockfile to remain unchanged.
        ctx: FastMCP request context.

    Returns:
        uv's command output.
    """
    command = ["sync"]
    if dry_run:
        command.append("--dry-run")
    if upgrade:
        command.append("--upgrade")
    if locked:
        command.append("--locked")
    return services(ctx).uv.run_uv_command(command)


@app.tool(name="lock", annotations=IDEMPOTENT)
def lock_dependencies(ctx: Context) -> str:
    """Update the project's lockfile.

    Args:
        ctx: FastMCP request context.

    Returns:
        uv's command output.
    """
    return services(ctx).uv.run_uv_command(["lock"])


@app.tool(name="run_script")
def run_script(ctx: Context, script_path: str) -> str:
    """Run a PEP 723 script with uv.

    Args:
        script_path: Path to the script.
        ctx: FastMCP request context.

    Returns:
        Script output.
    """
    return services(ctx).uv.run_uv_command(["run", "--script", script_path])


@app.tool(name="run_tool")
def run_tool(ctx: Context, package: str, arguments: list[str] | None = None) -> str:
    """Run an ephemeral tool through uv.

    Args:
        package: Package or tool specification.
        arguments: Arguments passed to the installed executable.
        ctx: FastMCP request context.

    Returns:
        Tool output.
    """
    return services(ctx).uv.run_uv_command(["tool", "run", package, *(arguments or [])])


@app.tool(name="export_requirements")
def export_requirements(
    ctx: Context,
    file_format: str = "requirements-txt",
    output_file: str | None = None,
    project_path: str | None = None,
) -> ExportResult:
    """Export the project lockfile to a requirements format.

    Args:
        file_format: uv export format, such as ``requirements-txt``.
        output_file: Optional output path. Without it, content is returned.
        project_path: Optional project working directory.
        ctx: FastMCP request context.

    Returns:
        Structured export result.
    """
    command = ["export", "--format", file_format]
    if output_file:
        command.extend(["--output-file", output_file])
    output = services(ctx).uv.run_uv_command(command, cwd=project_path)
    return ExportResult(
        file_format=file_format,
        output_file=output_file,
        content=None if output_file else output,
        success=True,
        message="Dependencies exported successfully.",
    )


@app.tool(name="build")
def build_project(ctx: Context, project_path: str | None = None) -> BuildResult:
    """Build source and wheel distributions for a project.

    Args:
        project_path: Optional project working directory.
        ctx: FastMCP request context.

    Returns:
        Build result with discovered artifacts.
    """
    project = Path(project_path or ".").resolve()
    output = services(ctx).uv.run_uv_command(["build"], cwd=project)
    dist = project / "dist"
    artifacts = (
        sorted(
            str(path.relative_to(project)) for path in dist.iterdir() if path.is_file()
        )
        if dist.is_dir()
        else []
    )
    return BuildResult(
        project_path=str(project),
        artifacts=artifacts,
        success=True,
        message=output.strip() or "Build completed successfully.",
    )


@app.tool(name="publish", annotations=DESTRUCTIVE)
def publish_project(
    ctx: Context,
    project_path: str | None = None,
    token: str | None = None,
) -> PublishResult:
    """Publish project distributions to the configured package index.

    Args:
        project_path: Optional project working directory.
        token: Optional publish token, never included in the result.
        ctx: FastMCP request context.

    Returns:
        Publish result.
    """
    env = {"UV_PUBLISH_TOKEN": token} if token else None
    project = Path(project_path or ".").resolve()
    output = services(ctx).uv.run_uv_command(["publish"], cwd=project, env=env)
    return PublishResult(
        project_path=str(project),
        success=True,
        message=output.strip() or "Project published successfully.",
    )


@app.tool(name="bump_version")
def bump_version(
    ctx: Context,
    level: str = "patch",
    project_path: str | None = None,
    dry_run: bool = False,
) -> BumpResult:
    """Bump a project's version using ``uv version``.

    Args:
        level: Bump level, such as ``major``, ``minor``, or ``patch``.
        project_path: Optional project working directory.
        dry_run: Calculate the change without writing it.
        ctx: FastMCP request context.

    Returns:
        Version bump result.
    """
    command = ["version", "--bump", level]
    if dry_run:
        command.append("--dry-run")
    output = services(ctx).uv.run_uv_command(command, cwd=project_path)
    match = re.search(r"from\s+(\S+)\s+to\s+(\S+)", output, re.IGNORECASE)
    return BumpResult(
        previous=match.group(1) if match else None,
        current=match.group(2) if match else None,
        success=True,
        message=output.strip() or "Version updated successfully.",
    )


@app.tool(name="manifest", annotations=READ_ONLY)
def project_manifest(project_path: str | None = None) -> ManifestResult:
    """Read a project's ``pyproject.toml`` using the standard library.

    Args:
        project_path: Project directory or direct path to ``pyproject.toml``.

    Returns:
        Parsed TOML manifest.

    Raises:
        ToolError: If the manifest cannot be found or parsed.
    """
    candidate = Path(project_path or ".")
    path = candidate / "pyproject.toml" if candidate.is_dir() else candidate
    try:
        with path.open("rb") as file:
            content = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ToolError(f"Could not read {path}: {e}") from e
    return ManifestResult(path=str(path.resolve()), content=content)


@app.tool(name="dependency_tree", annotations=READ_ONLY)
def dependency_tree(
    ctx: Context,
    depth: int | None = None,
    project_path: str | None = None,
) -> str:
    """Display the project's dependency tree.

    Args:
        depth: Optional maximum tree depth.
        project_path: Optional project working directory.
        ctx: FastMCP request context.

    Returns:
        The dependency tree text.
    """
    command = ["tree"]
    if depth is not None:
        command.extend(["--depth", str(depth)])
    return services(ctx).uv.run_uv_command(command, cwd=project_path)


@app.tool(name="format_code")
def format_code(ctx: Context, path: str | None = None) -> str:
    """Format Python code with an ephemeral Ruff installation.

    Args:
        path: File or directory to format. Defaults to the current directory.
        ctx: FastMCP request context.

    Returns:
        Ruff's output.
    """
    return services(ctx).uv.run_uv_command(
        ["tool", "run", "ruff", "format", path or "."]
    )


@app.tool(name="check")
def check_project(
    ctx: Context,
    project_path: str | None = None,
    fix: bool = False,
    locked: bool = False,
    frozen: bool = False,
    no_sync: bool = False,
    python: str | None = None,
    script: str | None = None,
) -> str:
    """Run checks on the project.

    Args:
        project_path: Optional project working directory.
        fix: Apply safe fixes to resolve type-checking errors.
        locked: Assert that the lockfile will remain unchanged.
        frozen: Check without updating the lockfile.
        no_sync: Avoid syncing the virtual environment.
        python: Python interpreter to use for the project environment.
        script: Run checks for the specified PEP 723 script instead.
        ctx: FastMCP request context.

    Returns:
        Check output.
    """
    command = ["check"]
    if fix:
        command.append("--fix")
    if locked:
        command.append("--locked")
    if frozen:
        command.append("--frozen")
    if no_sync:
        command.append("--no-sync")
    if python:
        command.extend(["--python", python])
    if script:
        command.extend(["--script", script])
    return services(ctx).uv.run_uv_command(command, cwd=project_path)


@app.tool(name="project_version", annotations=READ_ONLY)
def project_version(ctx: Context, project_path: str | None = None) -> ProjectVersion:
    """Read the current project version.

    Args:
        project_path: Optional project working directory.
        ctx: FastMCP request context.

    Returns:
        The project's package name and version.
    """
    document = services(ctx).uv.run_uv_json(
        ["version", "--output-format", "json"], cwd=project_path
    )
    return ProjectVersion(**document)
