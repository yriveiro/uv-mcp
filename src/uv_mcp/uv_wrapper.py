"""Generic uv CLI execution layer.

Exposes a thin wrapper around the uv executable: command execution with
virtual environment awareness, JSON output parsing, and the small set of
pip/venv helpers shared by multiple tools.
"""

import json
import logging
import os
import pathlib
import shlex
import subprocess
from pathlib import Path
from typing import Any

import uv

from uv_mcp.errors import UVCommandError, UVNotFoundError
from uv_mcp.models import OutdatedPackage, Package

logger = logging.getLogger(__name__)


def spec(package_name: str, version: str | None = None) -> str:
    """Return a package requirement string, pinning the version when given.

    Args:
        package_name: Name of the package.
        version: Optional exact version to pin.

    Returns:
        A PEP 508 requirement, e.g. ``requests==2.0`` when a version is given.
    """
    return f"{package_name}=={version}" if version else package_name


class UVWrapper:
    """Wrapper around the uv CLI with virtual environment support.

    Args:
        venv_path: Default virtual environment to activate for commands. When
            ``None``, looks for ``.venv`` or ``venv`` in the working directory.
        uv_binary: Path to the uv executable. When ``None``, discovered via
            :func:`uv.find_uv_bin`.
        command_timeout: Timeout in seconds for each uv command.
    """

    def __init__(
        self,
        venv_path: str | None = None,
        uv_binary: str | None = None,
        command_timeout: float | None = None,
    ):
        self.venv_path = self._resolve_venv_path(venv_path)
        self.uv_binary = uv_binary
        self.command_timeout = command_timeout
        logger.info("Using virtual environment: %s", self.venv_path)

    def _resolve_venv_path(self, venv_path: str | None) -> str | None:
        """Resolve the virtual environment path.

        Uses the provided path when given, otherwise checks for ``.venv`` or
        ``venv`` directories in the current directory.

        Returns:
            The absolute venv path, or ``None`` when no virtual environment
            could be found.
        """
        if venv_path:
            path = pathlib.Path(venv_path)
            if not path.exists():
                logger.warning(
                    "Specified virtual environment path %s does not exist", venv_path
                )
            return str(path.absolute())

        for venv_dir in (".venv", "venv"):
            path = pathlib.Path(venv_dir)
            if path.exists() and path.is_dir():
                return str(path.absolute())
        return None

    def run_uv_command(
        self,
        command: list[str],
        *,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> str:
        """Run a uv command and return its standard output.

        Args:
            command: List of command arguments without the ``uv`` prefix.
            cwd: Directory to run the command in.
            env: Extra environment variables merged over the inherited
                environment.
            check: Raise on non-zero exit codes. Disable for commands that
                report findings through their exit code, such as ``uv audit``.

        Returns:
            The command's standard output.

        Raises:
            UVNotFoundError: If the uv executable cannot be located.
            UVCommandError: If the command exits with a non-zero status and
                ``check`` is enabled.
        """
        try:
            uv_bin = self.uv_binary or uv.find_uv_bin()
            full_command = [uv_bin, *command]

            environment = os.environ.copy()
            if self.venv_path:
                environment["VIRTUAL_ENV"] = self.venv_path
                environment["PATH"] = (
                    os.path.join(self.venv_path, "bin")
                    + os.pathsep
                    + environment["PATH"]
                )
            if env:
                environment.update(env)

            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=False,
                env=environment,
                cwd=str(cwd) if cwd else None,
                timeout=self.command_timeout,
            )

            if result.returncode != 0 and check:
                cmd_str = " ".join(shlex.quote(arg) for arg in full_command)
                raise UVCommandError(cmd_str, result.returncode, result.stderr)

            return result.stdout

        except subprocess.TimeoutExpired as e:
            cmd_str = " ".join(shlex.quote(arg) for arg in full_command)
            raise UVCommandError(
                cmd_str,
                -1,
                f"command timed out after {self.command_timeout} seconds",
            ) from e
        except FileNotFoundError as e:
            raise UVNotFoundError(
                "UV executable not found or could not be executed"
            ) from e

    def run_uv_json(
        self,
        command: list[str],
        *,
        cwd: str | Path | None = None,
        check: bool = True,
    ) -> Any:
        """Run a uv command and parse its standard output as JSON.

        Args:
            command: List of command arguments without the ``uv`` prefix.
            cwd: Directory to run the command in.

        Returns:
            The parsed JSON document.

        Raises:
            UVCommandError: If the output is not valid JSON.
        """
        if cwd is None and check:
            output = self.run_uv_command(command)
        else:
            output = self.run_uv_command(command, cwd=cwd, check=check)
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise UVCommandError(
                " ".join(shlex.quote(arg) for arg in command),
                0,
                f"expected JSON output: {e}",
            ) from e

    @staticmethod
    def _python_flag(venv_path: str | None) -> list[str]:
        """Return the uv flag targeting a virtual environment's interpreter."""
        if not venv_path:
            return []
        return ["--python", str(pathlib.Path(venv_path) / "bin" / "python")]

    def list_installed_packages(self, venv_path: str | None = None) -> list[Package]:
        """List all packages installed in an environment.

        Args:
            venv_path: Optional virtual environment to inspect.

        Returns:
            The installed packages.
        """
        return [
            Package(**package)
            for package in self.run_uv_json(
                ["pip", "list", *self._python_flag(venv_path), "--format", "json"]
            )
        ]

    def list_packages_in_venv(self, venv_path: str) -> list[Package]:
        """List all packages installed in a specific virtual environment."""
        return self.list_installed_packages(venv_path=venv_path)

    def get_outdated_packages(
        self, venv_path: str | None = None
    ) -> list[OutdatedPackage]:
        """List installed packages with newer versions available.

        Args:
            venv_path: Optional virtual environment to inspect.

        Returns:
            The outdated packages.
        """
        return [
            OutdatedPackage(**package)
            for package in self.run_uv_json(
                [
                    "pip",
                    "list",
                    *self._python_flag(venv_path),
                    "--outdated",
                    "--format",
                    "json",
                ]
            )
        ]

    def get_package_info(self, package_name: str) -> str:
        """Show detailed information about a specific package."""
        return self.run_uv_command(["pip", "show", package_name])

    def add_dependency(self, package_name: str, version: str | None = None) -> str:
        """Add a dependency to the project."""
        return self.run_uv_command(["add", spec(package_name, version)])

    def remove_dependency(self, package_name: str) -> str:
        """Remove a dependency from the project."""
        return self.run_uv_command(["remove", package_name])

    def install_package(
        self,
        package_name: str,
        version: str | None = None,
        venv_path: str | None = None,
    ) -> str:
        """Install a package with pip, optionally into a virtual environment."""
        return self.run_uv_command(
            [
                "pip",
                "install",
                *self._python_flag(venv_path),
                spec(package_name, version),
            ]
        )

    def uninstall_package(self, package_name: str, venv_path: str | None = None) -> str:
        """Uninstall a package with pip, optionally from a virtual environment."""
        return self.run_uv_command(
            ["pip", "uninstall", *self._python_flag(venv_path), package_name]
        )

    def create_virtualenv(self, path: str, packages: list[str] | None = None) -> str:
        """Create a new virtual environment, optionally installing packages.

        Args:
            path: Where to create the environment.
            packages: Optional packages to install into the new environment.

        Returns:
            The output of the venv creation command.
        """
        output = self.run_uv_command(["venv", path])
        for package in packages or []:
            self.install_package(package, venv_path=path)
        return output
