# uv-mcp

A Model Context Protocol (MCP) server for interacting with Python installations via uv, the fast Python package installer.

## Overview

uv-mcp provides LLMs with direct access to inspect and manage Python environments through the [uv](https://github.com/astral-sh/uv) package manager. This allows AI assistants to help with Python dependency management, environment inspection, and troubleshooting tasks.

## Features

- **Environment Inspection**: Query installed packages and their versions
- **Environment Comparison**: Identify differences between virtual environments
- **Requirement Management**: Parse requirements.txt and pyproject.toml files
- **Package Information**: Retrieve metadata about PyPI packages
- **Virtual Environment Management**: Create and inspect virtual environments
- **UV Documentation**: Browse cached CLI, settings, and resolver documentation
- **Documentation Search**: Search the cached UV documentation from an MCP client
- **Python Management**: Discover, install, pin, upgrade, and remove Python versions
- **Tool Management**: Install, upgrade, list, and uninstall global uv tools
- **Security Auditing**: Audit project dependencies and installed uv tools for vulnerabilities and adverse package statuses
- **Diagnostics**: Diagnose, repair, and self-heal project environments

## How It Works

uv-mcp implements the [Model Context Protocol](https://modelcontextprotocol.io) to expose Python environment data and package management functionality through standardized resources and tools.

### Resources

- `python:packages://installed` - List of all installed packages and versions
- `python:packages://outdated` - List of installed packages with newer versions available
- `python:packages://{package_name}/info` - Detailed information about a package
- `python:requirements://{file_path*}` - Parsed requirements and version conflicts
- `uv:docs://{section}` - List entries in the `cli`, `settings`, or `resolver` sections
- `uv:docs://{section}/{command}` - Read documentation entry metadata
- `uv:docs://{section}/{command}/{subsection}` - Read detailed documentation content

### Tools

- `run(command: str[])` - Run a command or script
- `init()` - Create a new project
- `add(package_name: str, version: Optional[str])` - Add dependencies to the project
- `remove(package_name: str)` - Remove dependencies from the project
- `sync(dry_run: bool)` - Install all declared dependencies, uninstall anything not declared
- `lock()` - Update the project's lockfile
- `check(project_path: Optional[str], fix: bool)` - Check project metadata and dependencies
- `project_version(project_path: Optional[str])` - Read the project version
- `pip(command: str[])` - Run a pip command
- `create_virtualenv(path: str, packages: str[])` - Create a virtual environment
- `compare_environments(env1: str, env2: str)` - Compare packages in two environments
- `pip_install(package_name: str, version: Optional[str], venv_path: Optional[str])` - Install a package
- `pip_uninstall(package_name: str, venv_path: Optional[str])` - Uninstall a package
- `pip_list(venv_path: Optional[str])` - List packages in an optional target environment
- `outdated(venv_path: Optional[str])` - List installed packages with newer versions available
- `pip_show(packages: str[], venv_path: Optional[str])` - Show installed package metadata
- `pip_tree(venv_path: Optional[str])` / `pip_check(venv_path: Optional[str])` - Inspect environment dependencies
- `update_cache(force: bool)` - Refresh the UV documentation cache
- `search_documentation(query: str)` - Search cached UV documentation
- `python_list()` / `python_install(version)` / `python_pin(version)` - Manage Python installations
- `python_find(request)` / `python_upgrade(version)` / `python_uninstall(version)` - Resolve and update Python versions
- `tool_install(package)` / `tool_upgrade(name)` / `tool_list()` / `tool_uninstall(name)` - Manage uv tools
- `tool_dir(bin: bool)` / `tool_update_shell()` - Inspect and configure the uv tools directory
- `python_update_shell()` - Configure the uv-managed Python directory on `PATH`
- `workspace_metadata()` / `workspace_list()` / `workspace_dir(package?)` - Inspect workspaces
- `audit(...)` / `tool_audit(...)` - Audit project dependencies or installed uv tools for vulnerabilities
- `cache_clean(package)` / `cache_prune(ci)` / `cache_dir()` / `cache_size()` - Manage the uv cache
- `diagnose_environment(project_path)` / `repair_environment(project_path)` / `self_heal(project_path)` - Inspect and repair environments
- `pip_compile(input_file)` / `pip_sync(requirements_file)` / `pip_freeze()` - Run pip-compatible workflows
- `build(project_path)` / `publish(project_path)` / `bump_version(level)` - Build and publish projects
- `self_version()` / `self_update(target_version)` - Inspect and update uv

### Prompts

- `summarize_docs(section: Optional[str])` - Generate a prompt for summarizing UV documentation

## Usage

To start the server:

```bash
uvx uv-mcp
```

The server checks for `.venv` or `venv` in its working directory. To select an
explicit virtual environment, use the `serve` command:

```bash
uvx uv-mcp serve /path/to/.venv
```

Install the bundled Agent Skill into a project for agents that discover skills
from `.agents/skills`:

```bash
uvx uv-mcp skill install uv-mcp
```

Use `--target /path/to/project` to select another project directory, or
`--force` to replace an existing installation.

Configuration can also be provided through environment variables:

- `UV_MCP_VENV_PATH` - Default virtual environment path
- `UV_MCP_LOG_LEVEL` - Logging level, default `INFO`
- `UV_MCP_UV_BINARY` - Explicit path to the uv executable
- `UV_MCP_COMMAND_TIMEOUT` - Optional uv command timeout in seconds
- `UV_MCP_CACHE_DIR` - Documentation cache directory; defaults to the XDG cache directory

uv's optional malware check can be enabled for sync operations with
`UV_MALWARE_CHECK=1`.

## Development

This project is built with [FastMCP](https://github.com/PrefectHQ/fastmcp) and [uv](https://github.com/astral-sh/uv).
