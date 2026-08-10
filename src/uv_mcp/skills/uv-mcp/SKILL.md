---
name: uv-mcp
description: Manage Python projects and environments with uv (Rust-based pip/poetry/pyenv replacement). Use in Python projects (pyproject.toml, uv.lock, or .py files) when dependency management, virtual environments, package installation, script execution, or Python version management is needed. Prefers the uv-mcp tools (run, init, add, sync, lock, audit, tool_audit, pip_*, python_*, tool_*, diagnose_environment) combined into complete workflows; falls back to the uv CLI via bash. DO NOT load in JavaScript, TypeScript, or any non-Python project.
license: MIT
compatibility: Requires the uv CLI (>=0.12.2) installed and the uv-mcp server tools available in the MCP tool context.
allowed-tools: Bash(uv:*) Bash(uvx:*) Read
metadata:
  audience: python-developers
  author: Yago Riveiro
  version: "1.0.0"
---

# uv-mcp Skill

UV is a fast Python package/project manager (Rust). Replaces pip, pipx, poetry,
pyenv, virtualenv. This skill combines the uv-mcp server tools into complete,
verifiable workflows.

## Tool Priority

1. **MCP tools in your tool context** → use them (full catalog: `references/MCP-TOOLS.md`)
2. **Otherwise** → uv CLI via bash (see `## CLI Fallback`)

When you invoke a tool, verify the result before continuing: re-check with a
read-only tool (`pip_list`, `manifest`, `dependency_tree`, `audit`) whenever
the workflow has a verification step.

## Workflows

### Bootstrap a new project

1. `init(name, python_version, template: "app"|"lib")`
2. `add(package_name)` for each runtime dependency
3. `sync()` to install from the fresh lockfile
4. Verify: `dependency_tree()` shows the expected packages

### Add a dependency safely

1. `add(package_name, version?)`
2. `audit()` — scan for known vulnerabilities before syncing
3. `sync()` to install
4. If the audit found findings, prefer patched versions: `sync(upgrade=True)`
   then `audit()` again, or triage with `audit(ignore=[id])` /
   `audit(ignore_until_fixed=[id])` only after confirming the risk.

### Update dependencies

1. `lock()` to refresh the lockfile
2. `sync(upgrade=True)` to install newer versions
3. `audit()` — verify the update did not introduce vulnerabilities
4. `dependency_tree(depth?)` to review the change surface

### Triage a security audit

`audit()` returns a summary plus per-finding records. Escalate from:

- **Read the finding**: affected dependency, version range, and severity.
- **Fix first**: upgrade the package (`add(package_name, version)` with the
  patched version, or `sync(upgrade=True)`).
- **Scope**: `audit(no_dev=True)` / `audit(only_dev=True)` to separate
  production from development findings; `audit(script=path)` for PEP 723
  scripts.
- **Triage**: `ignore`/`ignore_until_fixed` for findings you consciously
  accept. Never suppress without stating the risk in your summary.

Audit `uv tool` installs with `tool_audit()` and upgrade findings with
`tool_upgrade(name?)`.

### Diagnose and repair an environment

1. `diagnose_environment(project_path?)` — checks manifest, venv, lockfile,
   and sync state; `healthy` flag summarizes the result.
2. If unhealthy: `repair_environment(project_path?)` (removes `.venv`, syncs).
3. If repair fails: `self_heal(project_path?)` (reinstall-first, recreates the
   venv on failure).
4. Verify: `diagnose_environment()` reports healthy.

Both repair tools are destructive — confirm with the user first.

### Release a version

1. `bump_version(level: "major"|"minor"|"patch", dry_run=True)` to preview
2. `bump_version(level)` to apply
3. `build(project_path?)` — confirm both sdist and wheel artifacts
4. `publish(project_path?, token?)` — token is passed via env, never logged
   (destructive; confirm with the user)

### Manage Python versions

1. `python_list()` — see installed and available versions
2. `python_install(version)` for a missing version
3. `python_pin(version, project_path?)` to pin the project's interpreter
4. `python_find(request?)` to resolve an interpreter path

### Manage uv tools (global CLIs)

1. `tool_list()` to inspect
2. `tool_install(package, version?, python?)` to add
3. `tool_audit()` to check for vulnerable tools
4. `tool_upgrade(name?)` to patch (all tools when no name given)
5. `tool_uninstall(name)` to remove (destructive)

### Run ad-hoc code

- `run(command: list[str])` — command in the project environment
- `run_script(script_path)` — PEP 723 inline scripts (auto-installs deps)
- `run_tool(package, arguments?)` — ephemeral one-off tool
- `format_code(path?)` — ephemeral Ruff formatting

### Pip-style workflows (legacy or explicit venvs)

- `pip_compile(input_file, output_file?, python?)` to pin requirements
- `pip_sync(requirements_file)` to install them (destructive)
- `pip_list(venv_path?)`, `outdated(venv_path?)`, `pip_freeze(venv_path?)` to inspect
- `pip_show(packages, venv_path?)`, `pip_tree(venv_path?)`, `pip_check(venv_path?)` for environment inspection
- `compare_environments(env1, env2)` to diff two venvs
- `create_virtualenv(path, packages?)` for ad-hoc venvs

### Project and workspace inspection

- `check(project_path?, fix?)` to validate project metadata and dependencies
- `project_version(project_path?)` to read the current project version
- `workspace_metadata()`, `workspace_list()`, `workspace_dir(package?)` to inspect workspaces

### Look up uv documentation

- `search_documentation(query)` — search cached UV docs; returns matching
  resource paths (`uv:docs://...`)
- `update_cache()` — refresh when docs are stale or a new uv version shipped
- `summarize_docs(section?)` — build a summary prompt over the cached docs

## CLI Fallback

Use when MCP tools are not in your tool context. Map each workflow step to the
equivalent command: `uv init`, `uv add`, `uv remove`, `uv sync`,
`uv lock`, `uv run`, `uv run --script`, `uv tool run`, `uv tool install`,
`uv venv`, `uv python install`, `uv python pin`, `uv pip ...`, `uv cache ...`,
`uv audit --output-format json`, `uv build`, `uv publish`, `uvx`.

## Rules

- MUST NOT use raw `pip install` or install packages into system Python — always use a venv or `uv tool install`
- MUST NOT use `@latest` tag — specify an explicit version for reproducibility
- MUST confirm with the user before any destructive tool: `remove`, `publish`, `pip_uninstall`, `pip_sync`, `cache_clean`, `cache_prune`, `tool_uninstall`, `python_uninstall`, `repair_environment`, `self_heal`, `self_update`
- A non-empty `audit()` result is a report, not an error — uv exits 1 when findings exist and the wrapper returns the parsed findings

## References

- Full tool catalog with signatures: `references/MCP-TOOLS.md`
- Project setup, venvs, Python pinning, PEP 723 scripts: `references/PROJECT-SETUP.md`
- Error handling and where to look up docs: `references/TROUBLESHOOTING.md`
