"""Exception hierarchy for uv command execution errors."""


class UVError(Exception):
    """Base exception for all UV command errors."""


class UVCommandError(UVError):
    """Raised when a UV command exits with a non-zero status.

    Attributes:
        command: The full command line that failed.
        returncode: Exit code of the process, or ``-1`` on timeout.
        stderr: Standard error output of the failed command.
    """

    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        message = f"UV command '{command}' failed with exit code {returncode}: {stderr}"
        super().__init__(message)


class UVNotFoundError(UVError):
    """Raised when the UV executable cannot be located or executed."""
