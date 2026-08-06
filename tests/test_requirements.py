from pathlib import Path

import pytest

from uv_mcp.requirements import RequirementsError, parse_requirements_file


def test_parse_requirements_txt_and_detects_conflicts(tmp_path: Path) -> None:
    path = tmp_path / "requirements-dev.txt"
    path.write_text("requests>=2\nrequests==1.0\n-r base.txt\n", encoding="utf-8")

    report = parse_requirements_file(path)

    assert report.source == "requirements.txt"
    assert [requirement.name for requirement in report.requirements] == [
        "requests",
        "requests",
    ]
    assert len(report.conflicts) == 1
    assert report.conflicts[0].package == "requests"
    assert report.conflicts[0].specifiers == "==1.0, >=2"


def test_parse_pyproject_includes_optional_dependencies(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        """
[project]
dependencies = ["fastmcp>=3"]

[project.optional-dependencies]
dev = ["pytest"]
""",
        encoding="utf-8",
    )

    report = parse_requirements_file(path)

    assert [requirement.name for requirement in report.requirements] == [
        "fastmcp",
        "pytest",
    ]


def test_parse_requirements_rejects_missing_files(tmp_path: Path) -> None:
    with pytest.raises(RequirementsError, match="file not found"):
        parse_requirements_file(tmp_path / "missing.txt")
