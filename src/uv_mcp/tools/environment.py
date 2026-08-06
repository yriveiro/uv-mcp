"""Virtual-environment inspection, diagnostics, and repair tools."""

import platform
import re
import shutil
from pathlib import Path

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.errors import UVCommandError, UVError
from uv_mcp.models import (
    CheckResult,
    DiagnosticCheck,
    DiagnosticReport,
    EnvironmentComparison,
    InstallInstructions,
    Package,
    RepairResult,
)
from uv_mcp.tools.common import DESTRUCTIVE, READ_ONLY, services


def _project_path(project_path: str | None) -> Path:
    """Resolve an optional project path."""
    return Path(project_path or ".").resolve()


def _check_command(
    ctx: Context, project: Path, name: str, command: list[str]
) -> DiagnosticCheck:
    """Run one diagnostic command and convert failures to check records."""
    try:
        output = services(ctx).uv.run_uv_command(command, cwd=project)
    except UVCommandError as e:
        return DiagnosticCheck(name=name, status="error", detail=e.stderr.strip())
    return DiagnosticCheck(name=name, status="ok", detail=output.strip() or "Passed.")


@app.tool(name="create_virtualenv")
def create_virtualenv(
    ctx: Context, path: str, packages: list[str] | None = None
) -> str:
    """Create a virtual environment and optionally install packages.

    Args:
        path: Environment path.
        packages: Optional packages to install.
        ctx: FastMCP request context.

    Returns:
        uv's command output.
    """
    return services(ctx).uv.create_virtualenv(path, packages)


@app.tool(
    name="compare_environments",
    annotations=READ_ONLY,
)
def compare_environments(ctx: Context, env1: str, env2: str) -> EnvironmentComparison:
    """Compare installed packages between two virtual environments.

    Args:
        env1: First environment path.
        env2: Second environment path.
        ctx: FastMCP request context.

    Returns:
        Package differences and an equality flag.
    """
    wrapper = services(ctx).uv
    packages1 = wrapper.list_packages_in_venv(env1)
    packages2 = wrapper.list_packages_in_venv(env2)
    versions1 = {package.name.lower(): package.version for package in packages1}
    versions2 = {package.name.lower(): package.version for package in packages2}
    only_in_env1 = [
        Package(name=name, version=versions1[name])
        for name in sorted(versions1.keys() - versions2.keys())
    ]
    only_in_env2 = [
        Package(name=name, version=versions2[name])
        for name in sorted(versions2.keys() - versions1.keys())
    ]
    differences = [
        (name, versions1[name], versions2[name])
        for name in sorted(versions1.keys() & versions2.keys())
        if versions1[name] != versions2[name]
    ]
    from uv_mcp.models import VersionDifference

    version_differences = [
        VersionDifference(name=name, env1=env1_version, env2=env2_version)
        for name, env1_version, env2_version in differences
    ]
    return EnvironmentComparison(
        env1=env1,
        env2=env2,
        only_in_env1=only_in_env1,
        only_in_env2=only_in_env2,
        version_differences=version_differences,
        identical=not (only_in_env1 or only_in_env2 or version_differences),
    )


@app.tool(name="check_installation", annotations=READ_ONLY)
def check_installation(ctx: Context) -> CheckResult:
    """Check whether uv is installed and report its version.

    Args:
        ctx: FastMCP request context.

    Returns:
        Installation status.
    """
    wrapper = services(ctx).uv
    try:
        output = wrapper.run_uv_command(["--version"]).strip()
    except UVError:
        return CheckResult(installed=False)
    match = re.search(r"\buv\s+(\S+)", output)
    return CheckResult(
        installed=True,
        version=match.group(1) if match else output,
        path=wrapper.uv_binary or shutil.which("uv"),
    )


@app.tool(name="install_instructions", annotations=READ_ONLY)
def install_instructions() -> InstallInstructions:
    """Return platform-specific instructions for installing uv.

    Returns:
        Installation instructions for the current operating system.
    """
    system = platform.system().lower()
    if system == "windows":
        command = (
            "powershell -ExecutionPolicy ByPass -c "
            '"irm https://astral.sh/uv/install.ps1 | iex"'
        )
        notes = "Restart the shell after installation."
    elif system == "darwin":
        command = "brew install uv"
        notes = "The Astral installer is also available for macOS."
    else:
        command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        notes = "Restart the shell or source the installer-modified PATH."
    return InstallInstructions(platform=system, command=command, notes=notes)


@app.tool(name="diagnose_environment", annotations=READ_ONLY)
def diagnose_environment(
    ctx: Context, project_path: str | None = None
) -> DiagnosticReport:
    """Diagnose a project's metadata, lockfile, and environment consistency.

    Args:
        project_path: Optional project directory.
        ctx: FastMCP request context.

    Returns:
        Structured diagnostic checks.
    """
    project = _project_path(project_path)
    checks = [
        DiagnosticCheck(
            name="pyproject.toml",
            status="ok" if (project / "pyproject.toml").is_file() else "error",
            detail=(
                "Project manifest found."
                if (project / "pyproject.toml").is_file()
                else "Project manifest not found."
            ),
        ),
        DiagnosticCheck(
            name="virtual_environment",
            status="ok"
            if any((project / name).is_dir() for name in (".venv", "venv"))
            else "warning",
            detail=(
                "A project virtual environment exists."
                if any((project / name).is_dir() for name in (".venv", "venv"))
                else "No .venv or venv directory found."
            ),
        ),
    ]
    if checks[0].status == "ok":
        checks.extend(
            (
                _check_command(ctx, project, "lockfile", ["lock", "--check"]),
                _check_command(ctx, project, "synchronization", ["sync", "--dry-run"]),
            )
        )
    return DiagnosticReport(
        project_path=str(project),
        checks=checks,
        healthy=all(check.status != "error" for check in checks),
    )


@app.tool(name="repair_environment", annotations=DESTRUCTIVE)
def repair_environment(ctx: Context, project_path: str | None = None) -> RepairResult:
    """Recreate a project's virtual environment and synchronize it.

    Args:
        project_path: Optional project directory.
        ctx: FastMCP request context.

    Returns:
        Repair result and performed actions.
    """
    project = _project_path(project_path)
    if not (project / "pyproject.toml").is_file():
        return RepairResult(
            project_path=str(project),
            success=False,
            actions=[],
            message="Project manifest not found.",
        )
    venv = project / ".venv"
    actions: list[str] = []
    if venv.exists():
        shutil.rmtree(venv)
        actions.append("Removed .venv.")
    services(ctx).uv.run_uv_command(["sync"], cwd=project)
    actions.append("Ran uv sync.")
    return RepairResult(
        project_path=str(project),
        success=True,
        actions=actions,
        message="Environment repaired successfully.",
    )


@app.tool(name="self_heal", annotations=DESTRUCTIVE)
def self_heal(ctx: Context, project_path: str | None = None) -> RepairResult:
    """Repair an environment with a reinstall-first strategy.

    Args:
        project_path: Optional project directory.
        ctx: FastMCP request context.

    Returns:
        Self-healing result and performed actions.
    """
    project = _project_path(project_path)
    actions = ["Ran uv sync --reinstall."]
    try:
        services(ctx).uv.run_uv_command(["sync", "--reinstall"], cwd=project)
    except UVCommandError:
        venv = project / ".venv"
        if venv.exists():
            shutil.rmtree(venv)
            actions.append("Removed .venv after reinstall failure.")
        services(ctx).uv.run_uv_command(["sync"], cwd=project)
        actions.append("Ran uv sync after recreating the environment.")
    return RepairResult(
        project_path=str(project),
        success=True,
        actions=actions,
        message="Environment self-healed successfully.",
    )
