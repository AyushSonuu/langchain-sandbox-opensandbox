"""OpenSandbox sandbox backend implementation."""

from __future__ import annotations

import shlex
from datetime import timedelta
from typing import TYPE_CHECKING

from deepagents.backends.protocol import (
    FILE_NOT_FOUND,
    INVALID_PATH,
    IS_DIRECTORY,
    PERMISSION_DENIED,
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox
from opensandbox.models import WriteEntry
from opensandbox.models.execd import RunCommandOpts

if TYPE_CHECKING:
    from opensandbox import SandboxSync

DEFAULT_FILE_MODE = 0o644


class OpenSandboxBackend(BaseSandbox):
    """OpenSandbox backend conforming to ``SandboxBackendProtocol``.

    Wraps an existing :class:`opensandbox.SandboxSync` instance and implements
    the three primitives required by :class:`~deepagents.backends.sandbox.BaseSandbox`
    (``execute``, ``upload_files``, ``download_files``). All higher-level file
    helpers (``ls``, ``read_file``, ``write_file``, ``glob``, ``grep``) are
    inherited from ``BaseSandbox`` and implemented on top of ``execute``.

    Example:
        .. code-block:: python

            from opensandbox import SandboxSync

            from langchain_opensandbox import OpenSandboxBackend

            sandbox = SandboxSync.create("python:3.12")
            backend = OpenSandboxBackend(sandbox=sandbox, timeout=300)
            result = backend.execute("echo hello")
            print(result.output)
    """

    def __init__(
        self,
        *,
        sandbox: SandboxSync,
        timeout: int = 30 * 60,
    ) -> None:
        """Create a backend wrapping an existing OpenSandbox sandbox.

        Args:
            sandbox: Existing OpenSandbox sandbox instance to wrap.
            timeout: Default command timeout in seconds used when ``execute()``
                is called without an explicit ``timeout``. A value of ``0``
                disables the server-side timeout (wait indefinitely).
        """
        self._sandbox = sandbox
        self._default_timeout = timeout

    @property
    def id(self) -> str:
        """Return the OpenSandbox sandbox id."""
        return self._sandbox.id

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute a shell command inside the sandbox.

        Args:
            command: Shell command string to execute.
            timeout: Maximum time in seconds to wait for the command to complete.
                If ``None``, uses the backend's default timeout. A value of ``0``
                disables the server-side timeout.

        Returns:
            The command output, exit code, and truncation flag.
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout
        opts = RunCommandOpts(
            timeout=timedelta(seconds=effective_timeout) if effective_timeout else None,
        )
        execution = self._sandbox.commands.run(command, opts=opts)

        # OpenSandbox streams stdout/stderr as one message per line, with the
        # trailing newline stripped. Rejoin with "\n" to reconstruct the output
        # (a single long line is delivered as one message, so this does not
        # introduce spurious breaks). A trailing newline cannot be recovered.
        stdout = "\n".join(msg.text for msg in execution.logs.stdout)
        stderr = "\n".join(msg.text for msg in execution.logs.stderr)

        output = stdout
        if stderr.strip():
            output += f"\n<stderr>{stderr.strip()}</stderr>"

        return ExecuteResponse(
            output=output,
            exit_code=execution.exit_code,
            truncated=False,
        )

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Upload files into the sandbox.

        Args:
            files: Pairs of ``(absolute_path, content_bytes)`` to write.

        Returns:
            One response per input file, in the same order. Paths that are not
            absolute are rejected with ``invalid_path``. Existing paths are
            rejected with an ``already exists`` error and left untouched, so a
            write never silently clobbers a file.
        """
        responses: list[FileUploadResponse] = []
        entries: list[WriteEntry] = []
        valid_indices: list[int] = []

        for i, (path, content) in enumerate(files):
            if not path.startswith("/"):
                responses.append(FileUploadResponse(path=path, error=INVALID_PATH))
                continue
            probe = self.execute(f"test -e {shlex.quote(path)}")
            if probe.exit_code == 0:
                responses.append(
                    FileUploadResponse(path=path, error=f"File already exists: {path}")
                )
                continue
            entries.append(WriteEntry(path=path, data=content, mode=DEFAULT_FILE_MODE))
            valid_indices.append(i)
            responses.append(FileUploadResponse(path=path, error=None))

        if entries:
            try:
                self._sandbox.files.write_files(entries)
            except Exception as exc:  # noqa: BLE001
                for i in valid_indices:
                    responses[i] = FileUploadResponse(path=files[i][0], error=str(exc))

        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download files from the sandbox.

        Args:
            paths: Absolute paths to read.

        Returns:
            One response per input path, in the same order. Non-absolute paths
            are rejected with ``invalid_path``; read failures are normalized to
            a ``FileOperationError`` code (``file_not_found``, ``is_directory``,
            ``permission_denied``) where possible, falling back to the raw error
            message otherwise.
        """
        responses: list[FileDownloadResponse] = []

        for path in paths:
            if not path.startswith("/"):
                responses.append(
                    FileDownloadResponse(path=path, content=None, error=INVALID_PATH)
                )
                continue
            try:
                content = self._sandbox.files.read_bytes(path)
            except Exception as exc:  # noqa: BLE001
                responses.append(
                    FileDownloadResponse(
                        path=path,
                        content=None,
                        error=self._classify_read_error(path, exc),
                    )
                )
            else:
                responses.append(
                    FileDownloadResponse(path=path, content=content, error=None)
                )

        return responses

    def _classify_read_error(self, path: str, exc: Exception) -> str:
        """Normalize a failed read into a ``FileOperationError`` code.

        Probes the path with a single command so the error the model sees is a
        stable code rather than a transport-specific SDK message.
        """
        quoted = shlex.quote(path)
        probe = self.execute(
            f"if [ -d {quoted} ]; then echo DIR; "
            f"elif [ ! -e {quoted} ]; then echo MISSING; "
            f"elif [ ! -r {quoted} ]; then echo NOREAD; "
            f"else echo OTHER; fi"
        )
        marker = probe.output.strip()
        if marker == "DIR":
            return IS_DIRECTORY
        if marker == "MISSING":
            return FILE_NOT_FOUND
        if marker == "NOREAD":
            return PERMISSION_DENIED
        message = str(exc)
        if "FILE_NOT_FOUND" in message or "no such file" in message.lower():
            return FILE_NOT_FOUND
        return message
