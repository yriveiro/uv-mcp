# uv-mcp Tool Catalog

All tools run through the uv-mcp server. Argument names match the MCP tool
signatures exactly. Tools marked **destructive** mutate state (install,
remove, publish, clean, uninstall) and require explicit user confirmation
before invocation. **read-only** tools never change state. Project tools run
in the current working directory unless a `project_path` argument is given.

## Project (`project` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `run` | `run(command: list[str])` | Run a command in the project environment |
| `init` | `init(name?, python_version?, path?, template: "app"\|"lib")` | Create a new project |
| `add` | `add(package_name, version?)` | Add a dependency to `pyproject.toml` |
| `remove` | `remove(package_name)` | Remove a dependency (destructive) |
| `sync` | `sync(dry_run?, upgrade?, locked?)` | Sync the environment from the lockfile (idempotent) |
| `lock` | `lock()` | Update the lockfile (idempotent) |
| `run_script` | `run_script(script_path)` | Run a PEP 723 inline-script |
| `run_tool` | `run_tool(package, arguments?)` | Run a package ephemerally (`uv tool run`) |
| `export_requirements` | `export_requirements(file_format?, output_file?, project_path?)` | Export lockfile to requirements format |
| `build` | `build(project_path?)` | Build source and wheel distributions |
| `publish` | `publish(project_path?, token?)` | Publish to the package index (destructive, token never logged) |
| `bump_version` | `bump_version(level: major\|minor\|patch, project_path?, dry_run?)` | Bump version via `uv version --bump` |
| `manifest` | `manifest(project_path?)` | Parse `pyproject.toml` into JSON (read-only) |
| `dependency_tree` | `dependency_tree(depth?, project_path?)` | Show the dependency tree (read-only) |
| `format_code` | `format_code(path?)` | Format Python code with ephemeral Ruff |
| `check` | `check(project_path?, fix?, locked?, frozen?, no_sync?, python?, script?)` | Run project checks |
| `project_version` | `project_version(project_path?)` | Read the project version (read-only) |

## Pip workflows (`pip` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `pip` | `pip(command: list[str])` | Arbitrary `uv pip` command |
| `pip_install` | `pip_install(package_name, version?, venv_path?)` | Install into a venv |
| `pip_uninstall` | `pip_uninstall(package_name, venv_path?)` | Uninstall from a venv (destructive) |
| `pip_list` | `pip_list(venv_path?)` | List installed packages (read-only) |
| `outdated` | `outdated(venv_path?)` | List installed packages with newer versions available (read-only) |
| `pip_show` | `pip_show(packages, venv_path?)` | Show installed package metadata (read-only) |
| `pip_tree` | `pip_tree(venv_path?, depth?, package?, invert?, outdated?)` | Display an environment dependency tree (read-only) |
| `pip_check` | `pip_check(venv_path?)` | Verify installed package compatibility (read-only) |
| `pip_compile` | `pip_compile(input_file, output_file?, python?)` | Pin an input requirements file |
| `pip_sync` | `pip_sync(requirements_file)` | Sync a venv to a requirements file (destructive) |
| `pip_freeze` | `pip_freeze(venv_path?)` | Freeze installed packages (read-only) |

## Python versions (`python` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `python_list` | `python_list()` | List Python installations (read-only) |
| `python_install` | `python_install(version)` | Install a managed Python |
| `python_pin` | `python_pin(version, project_path?)` | Pin a project's Python version |
| `python_find` | `python_find(request?)` | Resolve an interpreter path (read-only) |
| `python_upgrade` | `python_upgrade(version)` | Reinstall a managed Python (`--reinstall`) |
| `python_uninstall` | `python_uninstall(version)` | Remove a managed Python (destructive) |
| `python_dir` | `python_dir(which: "default"\|"bin")` | Show a managed Python directory (read-only) |
| `python_update_shell` | `python_update_shell()` | Add the managed Python directory to `PATH` (idempotent) |

## uv tools (`uv_tools` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `tool_install` | `tool_install(package, version?, python?)` | Install a global uv tool |
| `tool_upgrade` | `tool_upgrade(name?)` | Upgrade one or all uv tools |
| `tool_list` | `tool_list()` | List installed uv tools (read-only) |
| `tool_uninstall` | `tool_uninstall(name)` | Remove a uv tool (destructive) |
| `tool_dir` | `tool_dir(bin?)` | Show the uv tools directory (read-only) |
| `tool_update_shell` | `tool_update_shell()` | Add the uv tools directory to `PATH` (idempotent) |

## Workspace (`workspace` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `workspace_metadata` | `workspace_metadata(project_path?, script?)` | View workspace metadata (read-only) |
| `workspace_list` | `workspace_list(project_path?, paths?, scripts?)` | List workspace members (read-only) |
| `workspace_dir` | `workspace_dir(project_path?, package?)` | Show a workspace member path (read-only) |

## Cache (`uv_cache` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `cache_clean` | `cache_clean(package?)` | Clear cache entries (destructive) |
| `cache_prune` | `cache_prune(ci?)` | Prune dangling cache entries (destructive) |
| `cache_dir` | `cache_dir()` | Show the cache directory (read-only) |
| `cache_size` | `cache_size()` | Show cache size in bytes (read-only) |

## Security audit (`audit` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `audit` | `audit(project_path?, frozen?, locked?, no_dev?, only_dev?, ignore?, ignore_until_fixed?, python_version?, script?, offline?)` | Audit project dependencies for known vulnerabilities (read-only) |
| `tool_audit` | `tool_audit(tools?, all_tools?, ignore?, ignore_until_fixed?, offline?)` | Audit installed uv tools (read-only) |

Audit notes:

- `uv audit` exits with status 1 when findings exist; the wrapper handles this
  and returns the parsed report — a non-empty result is not an error.
- Returns a structured report: `summary` (audited packages, vulnerability and
  adverse-status counts), `vulnerabilities`, and `adverse_statuses`.
- `ignore` / `ignore_until_fixed` accept vulnerability IDs (e.g.
  `RUSTSEC-2023-0001`) for triage. `ignore_until_fixed` only suppresses while
  no fix is published.
- `script` audits a single PEP 723 script instead of the project.
- `no_dev` / `only_dev` scope the audit to production or development
  dependencies.

## Environment (`environment` domain)

| Tool | Signature | Behavior |
|---|---|---|
| `create_virtualenv` | `create_virtualenv(path, packages?)` | Create a venv, optionally with packages |
| `compare_environments` | `compare_environments(env1, env2)` | Diff packages between two venvs (read-only) |
| `check_installation` | `check_installation()` | Check uv is installed and report version (read-only) |
| `install_instructions` | `install_instructions()` | Platform-specific uv install commands (read-only) |
| `diagnose_environment` | `diagnose_environment(project_path?)` | Check manifest, venv, lockfile, sync state (read-only) |
| `repair_environment` | `repair_environment(project_path?)` | Delete `.venv` and re-sync (destructive) |
| `self_heal` | `self_heal(project_path?)` | `sync --reinstall`, then recreate venv on failure (destructive) |

## Docs and self (`docs_tools`, `self_tools` domains)

| Tool | Signature | Behavior |
|---|---|---|
| `search_documentation` | `search_documentation(query)` | Search cached UV docs (read-only) |
| `update_cache` | `update_cache(force?)` | Refresh cached UV documentation |
| `self_version` | `self_version()` | Show uv version (read-only) |
| `self_update` | `self_update()` | Update uv itself (destructive) |

## Prompt

| Prompt | Signature | Behavior |
|---|---|---|
| `summarize_docs` | `summarize_docs(section?)` | Generate a summary prompt for cached UV docs |
