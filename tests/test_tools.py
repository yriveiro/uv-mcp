import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastmcp import Context
from fastmcp.exceptions import ToolError

from uv_mcp.context import ServerContext
from uv_mcp.docs import CacheManager
from uv_mcp.models import DiagnosticReport
from uv_mcp.tools.audit import (
    audit_dependencies,
    audit_tools,
    parse_audit_output,
    parse_tool_audit_output,
)
from uv_mcp.tools.environment import diagnose_environment
from uv_mcp.tools.pip import outdated, pip_check, pip_show, pip_tree
from uv_mcp.tools.project import (
    bump_version,
    check_project,
    dependency_tree,
    init_project,
    project_manifest,
    project_version,
    run_tool,
)
from uv_mcp.tools.python import parse_python_list, python_dir, python_update_shell
from uv_mcp.tools.self_tools import self_update, self_version
from uv_mcp.tools.uv_cache import cache_size
from uv_mcp.tools.uv_tools import parse_tool_list, tool_dir, tool_update_shell
from uv_mcp.tools.workspace import workspace_dir, workspace_list, workspace_metadata
from uv_mcp.uv_wrapper import UVWrapper


class RecordingWrapper:
    """Small uv wrapper double that records command contracts."""

    def __init__(self, outputs: dict[tuple[str, ...], str] | None = None) -> None:
        self.outputs = outputs or {}
        self.calls: list[
            tuple[list[str], str | Path | None, dict[str, str] | None]
        ] = []
        self.checks: list[bool] = []
        self.uv_binary = "/usr/bin/uv"

    def run_uv_command(
        self,
        command: list[str],
        *,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> str:
        self.calls.append((command, cwd, env))
        self.checks.append(check)
        return self.outputs.get(tuple(command), "output")

    @staticmethod
    def _python_flag(venv_path: str | None) -> list[str]:
        return [] if venv_path is None else ["--python", f"{venv_path}/bin/python"]

    def run_uv_json(
        self,
        command: list[str],
        *,
        cwd: str | Path | None = None,
        check: bool = True,
    ) -> object:
        return json.loads(self.run_uv_command(command, cwd=cwd, check=check))


def context_for(wrapper: RecordingWrapper, tmp_path: Path) -> Context:
    """Build the minimal context shape consumed by tool functions."""
    fake_context = SimpleNamespace(
        lifespan_context=ServerContext(
            uv=cast(UVWrapper, wrapper),
            docs=CacheManager(tmp_path / "cache"),
        )
    )
    return cast(Context, fake_context)


def test_parse_python_list_preserves_machine_readable_fields() -> None:
    result = parse_python_list(
        """
        [
          {
            "key": "cpython-3.14.6-macos-aarch64-none",
            "version": "3.14.6",
            "path": "/opt/python3.14",
            "implementation": "cpython",
            "arch": "aarch64",
            "os": "macos",
            "managed": true
          }
        ]
        """
    )

    assert result.model_dump() == {
        "pythons": [
            {
                "key": "cpython-3.14.6-macos-aarch64-none",
                "version": "3.14.6",
                "path": "/opt/python3.14",
                "implementation": "cpython",
                "arch": "aarch64",
                "os": "macos",
                "managed": True,
            }
        ]
    }


def test_parse_tool_list_groups_executables_with_each_tool() -> None:
    result = parse_tool_list(
        """
        ruff v0.14.10
        - ruff
        aider-chat v0.81.1
        - aider
        - aider-chat
        """
    )

    assert [tool.model_dump() for tool in result.tools] == [
        {"name": "ruff", "version": "0.14.10", "executables": ["ruff"]},
        {
            "name": "aider-chat",
            "version": "0.81.1",
            "executables": ["aider", "aider-chat"],
        },
    ]


def test_outdated_returns_structured_packages_and_targets_venv(tmp_path: Path) -> None:
    venv_path = "/tmp/project/.venv"
    wrapper = RecordingWrapper(
        {
            (
                "pip",
                "list",
                "--python",
                f"{venv_path}/bin/python",
                "--outdated",
                "--format",
                "json",
            ): (
                '[{"name": "demo", "version": "1.0", '
                '"latest_version": "1.1", "latest_filetype": "wheel"}]'
            ),
        }
    )

    result = outdated(context_for(wrapper, tmp_path), venv_path)

    assert [package.model_dump() for package in result] == [
        {
            "name": "demo",
            "version": "1.0",
            "latest_version": "1.1",
            "latest_filetype": "wheel",
        }
    ]
    assert wrapper.calls[0][0] == [
        "pip",
        "list",
        "--python",
        f"{venv_path}/bin/python",
        "--outdated",
        "--format",
        "json",
    ]


def test_project_tools_cover_checks_and_version(tmp_path: Path) -> None:
    wrapper = RecordingWrapper(
        {
            ("version", "--output-format", "json"): (
                '{"package_name": "demo", "version": "1.2.3", "commit_info": null}'
            ),
        }
    )
    ctx = context_for(wrapper, tmp_path)

    assert (
        check_project(
            ctx,
            project_path=str(tmp_path),
            fix=True,
            locked=True,
            frozen=True,
            no_sync=True,
            python="3.14",
            script="demo.py",
        )
        == "output"
    )
    version = project_version(ctx, project_path=str(tmp_path))

    assert version.model_dump() == {
        "package_name": "demo",
        "version": "1.2.3",
        "commit_info": None,
    }
    assert [call[0] for call in wrapper.calls] == [
        [
            "check",
            "--fix",
            "--locked",
            "--frozen",
            "--no-sync",
            "--python",
            "3.14",
            "--script",
            "demo.py",
        ],
        ["version", "--output-format", "json"],
    ]
    assert [call[1] for call in wrapper.calls] == [str(tmp_path), str(tmp_path)]


def test_workspace_tools_parse_and_forward_options(tmp_path: Path) -> None:
    wrapper = RecordingWrapper(
        {
            (
                "workspace",
                "metadata",
                "--preview-features",
                "workspace-metadata",
            ): '{"workspace_root": "/tmp/workspace"}',
            ("workspace", "list", "--paths", "--scripts"): "demo\nscript.py\n",
            ("workspace", "dir", "--package", "demo"): "/tmp/workspace\n",
        }
    )
    ctx = context_for(wrapper, tmp_path)

    assert workspace_metadata(ctx) == {"workspace_root": "/tmp/workspace"}
    assert workspace_list(ctx, paths=True, scripts=True) == ["demo", "script.py"]
    assert workspace_dir(ctx, package="demo") == "/tmp/workspace"
    assert [call[0] for call in wrapper.calls] == [
        ["workspace", "metadata", "--preview-features", "workspace-metadata"],
        ["workspace", "list", "--paths", "--scripts"],
        ["workspace", "dir", "--package", "demo"],
    ]


def test_pip_inspection_tools_construct_commands(tmp_path: Path) -> None:
    wrapper = RecordingWrapper()
    ctx = context_for(wrapper, tmp_path)
    venv_path = "/tmp/project/.venv"

    assert pip_show(ctx, ["demo"], venv_path) == "output"
    assert (
        pip_tree(ctx, venv_path, depth=2, package="demo", invert=True, outdated=True)
        == "output"
    )
    assert pip_check(ctx, venv_path) == "output"

    assert [call[0] for call in wrapper.calls] == [
        ["pip", "show", "--python", f"{venv_path}/bin/python", "demo"],
        [
            "pip",
            "tree",
            "--python",
            f"{venv_path}/bin/python",
            "--depth",
            "2",
            "--package",
            "demo",
            "--invert",
            "--outdated",
        ],
        ["pip", "check", "--python", f"{venv_path}/bin/python"],
    ]
    assert wrapper.checks == [True, True, False]


def test_shell_and_directory_tools_construct_commands(tmp_path: Path) -> None:
    wrapper = RecordingWrapper({("tool", "dir", "--bin"): "/tmp/tools/bin\n"})
    ctx = context_for(wrapper, tmp_path)

    assert tool_dir(ctx, bin=True) == "/tmp/tools/bin"
    assert tool_update_shell(ctx) == "output"
    assert python_update_shell(ctx) == "output"
    assert [call[0] for call in wrapper.calls] == [
        ["tool", "dir", "--bin"],
        ["tool", "update-shell"],
        ["python", "update-shell"],
    ]


def test_python_dir_rejects_unknown_directory_kind(tmp_path: Path) -> None:
    wrapper = RecordingWrapper()
    ctx = context_for(wrapper, tmp_path)

    with pytest.raises(ValueError, match="default.*bin"):
        python_dir(ctx, "project")

    assert wrapper.calls == []


def test_project_tools_construct_commands_and_forward_working_directory(
    tmp_path: Path,
) -> None:
    wrapper = RecordingWrapper(
        {
            (
                "version",
                "--bump",
                "patch",
            ): "Bumped project version from 1.2.3 to 1.2.4",
        }
    )
    ctx = context_for(wrapper, tmp_path)

    result = bump_version(ctx, project_path=str(tmp_path))
    tree = dependency_tree(ctx, depth=2, project_path=str(tmp_path))
    tool_output = run_tool(ctx, "ruff", ["--version"])

    assert result.previous == "1.2.3"
    assert result.current == "1.2.4"
    assert result.success is True
    assert tree == "output"
    assert tool_output == "output"
    assert wrapper.calls == [
        (["version", "--bump", "patch"], str(tmp_path), None),
        (["tree", "--depth", "2"], str(tmp_path), None),
        (["tool", "run", "ruff", "--version"], None, None),
    ]


def test_init_constructs_project_options() -> None:
    wrapper = RecordingWrapper()
    result = init_project(
        context_for(wrapper, Path("/tmp")),
        name="demo",
        python_version="3.14",
        path="projects/demo",
        template="lib",
    )

    assert result == "output"
    assert wrapper.calls[0][0] == [
        "init",
        "--name",
        "demo",
        "--python",
        "3.14",
        "--lib",
        "projects/demo",
    ]


def test_self_update_reports_versions_without_exposing_credentials(
    tmp_path: Path,
) -> None:
    wrapper = RecordingWrapper(
        {
            ("--version",): "uv 0.12.1\n",
            ("self", "update", "0.12.2"): "updated",
        }
    )
    ctx = context_for(wrapper, tmp_path)

    before = self_version(ctx)
    result = self_update(ctx, "0.12.2")

    assert before.version == "0.12.1"
    assert result.model_dump() == {
        "success": True,
        "previous": "0.12.1",
        "current": "0.12.1",
        "message": "updated",
    }
    assert [call[0] for call in wrapper.calls] == [
        ["--version"],
        ["--version"],
        ["self", "update", "0.12.2"],
        ["--version"],
    ]


def test_cache_size_returns_directory_and_byte_count(tmp_path: Path) -> None:
    wrapper = RecordingWrapper(
        {
            ("cache", "dir"): "/tmp/uv-cache\n",
            ("cache", "size"): "26386567168\n",
        }
    )
    result = cache_size(context_for(wrapper, tmp_path))

    assert result.directory == "/tmp/uv-cache"
    assert result.size_bytes == 26386567168
    assert [call[0] for call in wrapper.calls] == [
        ["cache", "dir"],
        ["cache", "size"],
    ]


def test_manifest_reads_directory_and_reports_invalid_toml(tmp_path: Path) -> None:
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text('[project]\nname = "demo"\nversion = "1.0.0"\n')

    result = project_manifest(str(tmp_path))

    assert result.path == str(manifest.resolve())
    assert result.content["project"]["name"] == "demo"
    assert result.content["project"]["version"] == "1.0.0"

    manifest.write_text("[project\n")
    with pytest.raises(ToolError, match="Could not read"):
        project_manifest(str(tmp_path))


def test_diagnose_reports_manifest_and_command_failures(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    wrapper = RecordingWrapper(
        {
            ("lock", "--check"): "",
            ("sync", "--dry-run"): "Would install nothing.",
        }
    )
    report = diagnose_environment(context_for(wrapper, tmp_path), str(tmp_path))

    assert isinstance(report, DiagnosticReport)
    assert report.healthy is True
    assert {check.name for check in report.checks} == {
        "pyproject.toml",
        "virtual_environment",
        "lockfile",
        "synchronization",
    }
    assert [call[0] for call in wrapper.calls] == [
        ["lock", "--check"],
        ["sync", "--dry-run"],
    ]


def test_parse_audit_output_preserves_findings_and_statuses() -> None:
    result = parse_audit_output(
        """
        {
          "schema": {"version": "preview"},
          "summary": {
            "audited_packages": 2,
            "vulnerabilities": 1,
            "adverse_statuses": 1
          },
          "vulnerabilities": [{
            "dependency": {"name": "demo", "version": "1.0"},
            "id": "GHSA-demo",
            "display_id": "CVE-2026-0001",
            "aliases": ["CVE-2026-0001"],
            "summary": null,
            "description": "A test finding",
            "link": null,
            "fix_versions": ["1.1"],
            "published": null,
            "modified": null
          }],
          "adverse_statuses": [{
            "name": "legacy",
            "status": "deprecated",
            "reason": "Use replacement"
          }]
        }
        """
    )

    assert result.schema_version == "preview"
    assert result.vulnerabilities[0].dependency.name == "demo"
    assert result.vulnerabilities[0].fix_versions == ["1.1"]
    assert result.adverse_statuses[0].status == "deprecated"
    assert result.clean is False


def test_parse_tool_audit_output_supports_per_tool_reports() -> None:
    result = parse_tool_audit_output(
        """
        {
          "schema": {"version": "preview"},
          "tools": [{
            "name": "ruff",
            "summary": {
              "audited_packages": 1,
              "vulnerabilities": 0,
              "adverse_statuses": 0
            },
            "vulnerabilities": [],
            "adverse_statuses": []
          }]
        }
        """
    )

    assert result.tools[0].name == "ruff"
    assert result.clean is True


def test_audit_constructs_flags_and_allows_findings_exit(tmp_path: Path) -> None:
    wrapper = RecordingWrapper(
        {
            (
                "audit",
                "--output-format",
                "json",
                "--frozen",
                "--no-dev",
                "--ignore",
                "GHSA-demo",
                "--offline",
            ): """
            {"schema":{"version":"preview"},"summary":{"audited_packages":0,"vulnerabilities":0,"adverse_statuses":0},"vulnerabilities":[],"adverse_statuses":[]}
            """,
        }
    )

    result = audit_dependencies(
        context_for(wrapper, tmp_path),
        project_path=str(tmp_path),
        frozen=True,
        no_dev=True,
        ignore=["GHSA-demo"],
        offline=True,
    )

    assert result.clean is True
    assert wrapper.calls[0] == (
        [
            "audit",
            "--output-format",
            "json",
            "--frozen",
            "--no-dev",
            "--ignore",
            "GHSA-demo",
            "--offline",
        ],
        str(tmp_path),
        None,
    )
    assert wrapper.checks == [False]


def test_tool_audit_constructs_named_and_all_commands(tmp_path: Path) -> None:
    wrapper = RecordingWrapper(
        {
            (
                "tool",
                "audit",
                "--output-format",
                "json",
                "ruff",
                "--ignore-until-fixed",
                "GHSA-demo",
            ): """
            {"schema":{"version":"preview"},"tools":[]}
            """,
            ("tool", "audit", "--output-format", "json", "--all"): """
            {"schema":{"version":"preview"},"tools":[]}
            """,
        }
    )
    ctx = context_for(wrapper, tmp_path)

    audit_tools(ctx, tools=["ruff"], ignore_until_fixed=["GHSA-demo"])
    audit_tools(ctx)

    assert wrapper.calls[0][0] == [
        "tool",
        "audit",
        "--output-format",
        "json",
        "ruff",
        "--ignore-until-fixed",
        "GHSA-demo",
    ]
    assert wrapper.calls[1][0] == ["tool", "audit", "--output-format", "json", "--all"]
    assert wrapper.checks == [False, False]
