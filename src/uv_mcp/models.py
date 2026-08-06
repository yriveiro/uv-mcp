"""Typed models for data exchanged with MCP clients."""

from typing import Any, Literal

from pydantic import BaseModel


class Package(BaseModel):
    """A package installed in an environment."""

    name: str
    version: str


class OutdatedPackage(Package):
    """An installed package with a newer version available."""

    latest_version: str
    latest_filetype: str | None = None


class VersionDifference(BaseModel):
    """A package with different versions in two environments."""

    name: str
    env1: str
    env2: str


class EnvironmentComparison(BaseModel):
    """Result of comparing the packages of two virtual environments."""

    env1: str
    env2: str
    only_in_env1: list[Package]
    only_in_env2: list[Package]
    version_differences: list[VersionDifference]
    identical: bool


class RequirementRecord(BaseModel):
    """A single parsed requirement."""

    name: str
    specifier: str
    extras: list[str]
    marker: str | None
    url: str | None


class Conflict(BaseModel):
    """Incompatible version constraints for a package."""

    package: str
    specifiers: str


class RequirementsReport(BaseModel):
    """Parsed contents of a requirements file."""

    path: str
    source: Literal["requirements.txt", "pyproject.toml"]
    requirements: list[RequirementRecord]
    conflicts: list[Conflict]


class PythonInfo(BaseModel):
    """A Python installation known to uv."""

    key: str
    version: str
    path: str | None
    implementation: str
    arch: str
    os: str
    managed: bool = False


class PythonListResult(BaseModel):
    """Result of listing the available Python installations."""

    pythons: list[PythonInfo]


class PythonOperationResult(BaseModel):
    """Result of an operation on a Python installation."""

    version: str
    success: bool
    message: str
    path: str | None = None


class PythonFindResult(BaseModel):
    """Result of resolving a Python interpreter request."""

    request: str | None
    path: str


class PythonDirResult(BaseModel):
    """The uv Python directory for a given target."""

    which: str
    path: str


class ToolInfo(BaseModel):
    """A tool installed via ``uv tool install``."""

    name: str
    version: str
    executables: list[str]


class ToolListResult(BaseModel):
    """Result of listing the installed uv tools."""

    tools: list[ToolInfo]


class ToolOperationResult(BaseModel):
    """Result of installing, upgrading, or uninstalling a uv tool."""

    name: str
    success: bool
    message: str


class CacheInfo(BaseModel):
    """Information about uv's cache directory."""

    directory: str
    size_bytes: int | None = None


class CacheOperationResult(BaseModel):
    """Result of a cache cleanup operation."""

    success: bool
    message: str
    package: str | None = None


class CheckResult(BaseModel):
    """Result of checking whether uv is installed."""

    installed: bool
    version: str | None = None
    path: str | None = None


class InstallInstructions(BaseModel):
    """Instructions for installing uv on the current platform."""

    platform: str
    command: str
    notes: str


class DiagnosticCheck(BaseModel):
    """A single check performed during an environment diagnosis."""

    name: str
    status: Literal["ok", "warning", "error"]
    detail: str


class DiagnosticReport(BaseModel):
    """Result of diagnosing a project environment."""

    project_path: str
    checks: list[DiagnosticCheck]
    healthy: bool


class RepairResult(BaseModel):
    """Result of repairing or self-healing a project environment."""

    project_path: str
    success: bool
    actions: list[str]
    message: str


class ExportResult(BaseModel):
    """Result of exporting the project lockfile to another format."""

    file_format: str
    output_file: str | None
    content: str | None
    success: bool
    message: str


class BuildResult(BaseModel):
    """Result of building the project distributions."""

    project_path: str
    artifacts: list[str]
    success: bool
    message: str


class PublishResult(BaseModel):
    """Result of publishing distributions to an index."""

    project_path: str
    success: bool
    message: str


class BumpResult(BaseModel):
    """Result of bumping the project version."""

    previous: str | None
    current: str | None
    success: bool
    message: str


class ManifestResult(BaseModel):
    """Parsed contents of a project's ``pyproject.toml``."""

    path: str
    content: dict[str, Any]


class ProjectVersion(BaseModel):
    """The version of a project as reported by ``uv version``."""

    package_name: str
    version: str
    commit_info: dict[str, Any] | None = None


class SelfVersionResult(BaseModel):
    """The installed uv version."""

    version: str


class SelfUpdateResult(BaseModel):
    """Result of updating the uv executable."""

    success: bool
    previous: str | None
    current: str | None
    message: str


class AuditDependency(BaseModel):
    """A resolved dependency included in a security audit."""

    name: str
    version: str


class Vulnerability(BaseModel):
    """A known vulnerability affecting an audited dependency."""

    dependency: AuditDependency
    id: str
    display_id: str | None = None
    aliases: list[str] = []
    summary: str | None = None
    description: str | None = None
    link: str | None = None
    fix_versions: list[str] = []
    published: str | None = None
    modified: str | None = None


class AdverseStatus(BaseModel):
    """An adverse project status reported by an audit (PEP 792)."""

    name: str
    status: Literal["archived", "quarantined", "deprecated"]
    reason: str | None = None


class AuditSummary(BaseModel):
    """Counts of findings in an audit report."""

    audited_packages: int
    vulnerabilities: int
    adverse_statuses: int


class AuditResult(BaseModel):
    """Result of auditing a project's dependencies."""

    schema_version: str
    summary: AuditSummary
    vulnerabilities: list[Vulnerability]
    adverse_statuses: list[AdverseStatus]

    @property
    def clean(self) -> bool:
        """True when the audit found no vulnerabilities or adverse statuses."""
        return self.summary.vulnerabilities == 0 and self.summary.adverse_statuses == 0


class ToolAuditReport(BaseModel):
    """Audit findings for a single installed uv tool."""

    name: str
    summary: AuditSummary
    vulnerabilities: list[Vulnerability]
    adverse_statuses: list[AdverseStatus]


class ToolAuditResult(BaseModel):
    """Result of auditing installed uv tools."""

    schema_version: str
    tools: list[ToolAuditReport]

    @property
    def clean(self) -> bool:
        """True when no audited tool has findings."""
        return all(
            report.summary.vulnerabilities == 0 and report.summary.adverse_statuses == 0
            for report in self.tools
        )
