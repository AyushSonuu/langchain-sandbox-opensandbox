from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import langchain_opensandbox
from langchain_opensandbox.sandbox import OpenSandboxBackend


def _make_execution(
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int | None = 0,
) -> SimpleNamespace:
    logs = SimpleNamespace(
        stdout=[SimpleNamespace(text=stdout)] if stdout else [],
        stderr=[SimpleNamespace(text=stderr)] if stderr else [],
    )
    return SimpleNamespace(logs=logs, exit_code=exit_code)


def _make_backend() -> tuple[OpenSandboxBackend, MagicMock]:
    mock_sdk = MagicMock()
    mock_sdk.id = "sb-123"
    # Default probe result: `test -e`/classification commands report "does not
    # exist" so uploads proceed and downloads fall through to the raw message.
    mock_sdk.commands.run.return_value = _make_execution(exit_code=1)
    return OpenSandboxBackend(sandbox=mock_sdk), mock_sdk


def test_import() -> None:
    assert langchain_opensandbox is not None
    assert isinstance(langchain_opensandbox.__version__, str)


def test_id() -> None:
    sb, _ = _make_backend()
    assert sb.id == "sb-123"


def test_execute_returns_stdout() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.commands.run.return_value = _make_execution(
        stdout="hello world", exit_code=0
    )

    result = sb.execute("echo hello world")

    assert result.output == "hello world"
    assert result.exit_code == 0
    assert result.truncated is False


def test_execute_appends_stderr() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.commands.run.return_value = _make_execution(
        stdout="out", stderr="boom", exit_code=1
    )

    result = sb.execute("false")

    assert "out" in result.output
    assert "<stderr>boom</stderr>" in result.output
    assert result.exit_code == 1


def test_execute_none_exit_code_preserved() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.commands.run.return_value = _make_execution(stdout="x", exit_code=None)

    result = sb.execute("echo x")

    # None means "could not be determined" (e.g. timeout/kill); it must not be
    # coerced to 0, which would report a non-completing command as success.
    assert result.exit_code is None


def test_upload_rejects_relative_paths() -> None:
    sb, mock_sdk = _make_backend()

    responses = sb.upload_files([("relative.txt", b"data")])

    assert responses[0].error == "invalid_path"
    mock_sdk.files.write_files.assert_not_called()


def test_upload_writes_absolute_paths() -> None:
    sb, mock_sdk = _make_backend()

    responses = sb.upload_files([("/tmp/a.txt", b"data")])

    assert responses[0].error is None
    assert mock_sdk.files.write_files.call_count == 1


def test_upload_rejects_existing_file() -> None:
    sb, mock_sdk = _make_backend()
    # `test -e` reports the path already exists.
    mock_sdk.commands.run.return_value = _make_execution(exit_code=0)

    responses = sb.upload_files([("/tmp/a.txt", b"data")])

    assert "already exists" in responses[0].error.lower()
    mock_sdk.files.write_files.assert_not_called()


def test_download_rejects_relative_paths() -> None:
    sb, mock_sdk = _make_backend()

    responses = sb.download_files(["relative.txt"])

    assert responses[0].error == "invalid_path"
    mock_sdk.files.read_bytes.assert_not_called()


def test_download_returns_content() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.files.read_bytes.return_value = b"file-bytes"

    responses = sb.download_files(["/tmp/a.txt"])

    assert responses[0].content == b"file-bytes"
    assert responses[0].error is None


def test_download_maps_missing_to_file_not_found() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.files.read_bytes.side_effect = RuntimeError("boom")
    mock_sdk.commands.run.return_value = _make_execution(stdout="MISSING", exit_code=0)

    responses = sb.download_files(["/tmp/missing.txt"])

    assert responses[0].content is None
    assert responses[0].error == "file_not_found"


def test_download_maps_directory_to_is_directory() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.files.read_bytes.side_effect = RuntimeError("boom")
    mock_sdk.commands.run.return_value = _make_execution(stdout="DIR", exit_code=0)

    responses = sb.download_files(["/tmp/dir"])

    assert responses[0].error == "is_directory"


def test_download_maps_unreadable_to_permission_denied() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.files.read_bytes.side_effect = RuntimeError("boom")
    mock_sdk.commands.run.return_value = _make_execution(stdout="NOREAD", exit_code=0)

    responses = sb.download_files(["/tmp/secret"])

    assert responses[0].error == "permission_denied"


def test_download_falls_back_to_raw_error() -> None:
    sb, mock_sdk = _make_backend()
    mock_sdk.files.read_bytes.side_effect = RuntimeError("weird transport error")
    mock_sdk.commands.run.return_value = _make_execution(stdout="OTHER", exit_code=0)

    responses = sb.download_files(["/tmp/x.txt"])

    assert responses[0].content is None
    assert "weird transport error" in responses[0].error
