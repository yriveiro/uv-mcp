"""Security audit tools backed by ``uv audit`` and ``uv tool audit``."""

import json
from typing import Any

from fastmcp import Context

from uv_mcp.app import app
from uv_mcp.models import (
    AdverseStatus,
    AuditResult,
    AuditSummary,
    ToolAuditReport,
    ToolAuditResult,
    Vulnerability,
)
from uv_mcp.tools.common import READ_ONLY, services


def _audit_body(document: dict[str, Any]) -> dict[str, Any]:
    """Return the report body shared by project and tool audit output."""
    return {
        "summary": AuditSummary(**document["summary"]),
        "vulnerabilities": [
            Vulnerability(**finding) for finding in document["vulnerabilities"]
        ],
        "adverse_statuses": [
            AdverseStatus(**status) for status in document["adverse_statuses"]
        ],
    }


def parse_audit_output(output: str) -> AuditResult:
    """Parse ``uv audit --output-format json`` output.

    Args:
        output: JSON output from uv.

    Returns:
        Parsed project audit report.
    """
    document = json.loads(output)
    return AuditResult(
        schema_version=document["schema"]["version"], **_audit_body(document)
    )


def parse_tool_audit_output(output: str) -> ToolAuditResult:
    """Parse ``uv tool audit --output-format json`` output.

    Args:
        output: JSON output from uv.

    Returns:
        Parsed per-tool audit reports.
    """
    document = json.loads(output)
    return ToolAuditResult(
        schema_version=document["schema"]["version"],
        tools=[
            ToolAuditReport(name=tool["name"], **_audit_body(tool))
            for tool in document["tools"]
        ],
    )


def _audit_flags(
    *,
    frozen: bool,
    locked: bool,
    no_dev: bool,
    only_dev: bool,
    ignore: list[str] | None,
    ignore_until_fixed: list[str] | None,
    python_version: str | None,
    script: str | None,
    offline: bool,
) -> list[str]:
    """Build shared project audit flags."""
    flags: list[str] = []
    if frozen:
        flags.append("--frozen")
    if locked:
        flags.append("--locked")
    if no_dev:
        flags.append("--no-dev")
    if only_dev:
        flags.append("--only-dev")
    for identifier in ignore or []:
        flags.extend(["--ignore", identifier])
    for identifier in ignore_until_fixed or []:
        flags.extend(["--ignore-until-fixed", identifier])
    if python_version:
        flags.extend(["--python-version", python_version])
    if script:
        flags.extend(["--script", script])
    if offline:
        flags.append("--offline")
    return flags


@app.tool(name="audit", annotations=READ_ONLY)
def audit_dependencies(
    ctx: Context,
    project_path: str | None = None,
    frozen: bool = False,
    locked: bool = False,
    no_dev: bool = False,
    only_dev: bool = False,
    ignore: list[str] | None = None,
    ignore_until_fixed: list[str] | None = None,
    python_version: str | None = None,
    script: str | None = None,
    offline: bool = False,
) -> AuditResult:
    """Audit project dependencies for known vulnerabilities and adverse statuses.

    Args:
        project_path: Optional project working directory.
        frozen: Audit requirements without locking the project.
        locked: Require the lockfile to remain unchanged.
        no_dev: Exclude the development dependency group.
        only_dev: Audit only the development dependency group.
        ignore: Vulnerability IDs to ignore.
        ignore_until_fixed: IDs to ignore only while no fix is available.
        python_version: Python version to audit against.
        script: Audit a PEP 723 script instead of the project.
        offline: Use only cached advisory data.
        ctx: FastMCP request context.

    Returns:
        Structured audit report.
    """
    command = ["audit", "--output-format", "json"]
    command.extend(
        _audit_flags(
            frozen=frozen,
            locked=locked,
            no_dev=no_dev,
            only_dev=only_dev,
            ignore=ignore,
            ignore_until_fixed=ignore_until_fixed,
            python_version=python_version,
            script=script,
            offline=offline,
        )
    )
    output = services(ctx).uv.run_uv_command(command, cwd=project_path, check=False)
    return parse_audit_output(output)


@app.tool(name="tool_audit", annotations=READ_ONLY)
def audit_tools(
    ctx: Context,
    tools: list[str] | None = None,
    all_tools: bool = True,
    ignore: list[str] | None = None,
    ignore_until_fixed: list[str] | None = None,
    offline: bool = False,
) -> ToolAuditResult:
    """Audit installed uv tools for known vulnerabilities.

    Args:
        tools: Names of specific installed tools to audit.
        all_tools: Audit all installed tools when no names are provided.
        ignore: Vulnerability IDs to ignore.
        ignore_until_fixed: IDs to ignore only while no fix is available.
        offline: Use only cached advisory data.
        ctx: FastMCP request context.

    Returns:
        Structured per-tool audit report.
    """
    command = ["tool", "audit", "--output-format", "json"]
    if tools:
        command.extend(tools)
    elif all_tools:
        command.append("--all")
    for identifier in ignore or []:
        command.extend(["--ignore", identifier])
    for identifier in ignore_until_fixed or []:
        command.extend(["--ignore-until-fixed", identifier])
    if offline:
        command.append("--offline")
    output = services(ctx).uv.run_uv_command(command, check=False)
    return parse_tool_audit_output(output)
