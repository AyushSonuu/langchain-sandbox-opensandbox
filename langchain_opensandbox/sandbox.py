"""OpenSandbox sandbox backend implementation."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from deepagents.backends.protocol import (
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

        stdout = "".join(msg.text for msg in execution.logs.stdout)
        stderr = "".join(msg.text for msg in execution.logs.stderr)

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
            absolute are rejected with ``invalid_path``.
        """
        responses: list[FileUploadResponse] = []
        entries: list[WriteEntry] = []
        valid_indices: list[int] = []

        for i, (path, content) in enumerate(files):
            if not path.startswith("/"):
                responses.append(FileUploadResponse(path=path, error="invalid_path"))
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
            are rejected with ``invalid_path``; read failures carry the error
            message.
        """
        responses: list[FileDownloadResponse] = []

        for path in paths:
            if not path.startswith("/"):
                responses.append(
                    FileDownloadResponse(path=path, content=None, error="invalid_path")
                )
                continue
            try:
                content = self._sandbox.files.read_bytes(path)
                responses.append(
                    FileDownloadResponse(path=path, content=content, error=None)
                )
            except Exception as exc:  # noqa: BLE001
                responses.append(
                    FileDownloadResponse(path=path, content=None, error=str(exc))
                )

        return responses
