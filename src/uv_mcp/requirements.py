"""Parsing of Python requirement files (requirements.txt, pyproject.toml)."""

import pathlib
import tomllib

from packaging.requirements import InvalidRequirement, Requirement

from uv_mcp.models import Conflict, RequirementRecord, RequirementsReport


class RequirementsError(Exception):
    """Raised when a requirements file cannot be parsed."""


def _parse_requirement_line(line: str) -> RequirementRecord:
    """Parse a single requirement line into a structured record."""
    requirement = Requirement(line)
    return RequirementRecord(
        name=requirement.name,
        specifier=str(requirement.specifier) or "*",
        extras=sorted(requirement.extras),
        marker=str(requirement.marker) if requirement.marker else None,
        url=requirement.url,
    )


def _parse_requirements_txt(content: str) -> list[RequirementRecord]:
    requirements = []
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-r", "--requirement", "-c", "--constraint")):
            continue
        if line.startswith(("-e", "--editable")):
            continue
        try:
            requirements.append(_parse_requirement_line(line))
        except InvalidRequirement as e:
            raise RequirementsError(f"invalid requirement {line!r}: {e}") from e
    return requirements


def _parse_pyproject(content: str) -> list[RequirementRecord]:
    project = tomllib.loads(content).get("project", {})
    groups = project.get("optional-dependencies", {})
    requirements = []
    for name in ["dependencies"] + sorted(groups):
        lines = project.get(name, []) if name == "dependencies" else groups[name]
        for line in lines:
            try:
                requirements.append(_parse_requirement_line(line))
            except InvalidRequirement as e:
                raise RequirementsError(f"invalid requirement {line!r}: {e}") from e
    return requirements


def parse_requirements_file(
    path: str | pathlib.Path,
) -> RequirementsReport:
    """Parse a requirements.txt or pyproject.toml file.

    Returns a structured report with the parsed requirements, the source
    type, and any conflicts detected between pinned versions.
    """
    path = pathlib.Path(path).expanduser()
    if not path.is_file():
        raise RequirementsError(f"file not found: {path}")

    content = path.read_text(encoding="utf-8")
    if path.name == "pyproject.toml":
        requirements = _parse_pyproject(content)
        source = "pyproject.toml"
    else:
        requirements = _parse_requirements_txt(content)
        source = "requirements.txt"

    return RequirementsReport(
        path=str(path),
        source=source,
        requirements=requirements,
        conflicts=_detect_conflicts(requirements),
    )


def _detect_conflicts(
    requirements: list[RequirementRecord],
) -> list[Conflict]:
    """Flag requirements that pin the same package to incompatible versions."""
    versions: dict[str, set[str]] = {}
    for requirement in requirements:
        versions.setdefault(requirement.name.lower(), set()).add(requirement.specifier)

    return [
        Conflict(package=name, specifiers=", ".join(sorted(specifiers)))
        for name, specifiers in sorted(versions.items())
        if len(specifiers) > 1
    ]
