# langchain-opensandbox

[![PyPI - Version](https://img.shields.io/pypi/v/langchain-opensandbox?label=%20)](https://pypi.org/project/langchain-opensandbox/#history)
[![PyPI - License](https://img.shields.io/pypi/l/langchain-opensandbox)](https://opensource.org/licenses/Apache-2.0)
[![PyPI - Downloads](https://img.shields.io/pepy/dt/langchain-opensandbox)](https://pypistats.org/packages/langchain-opensandbox)

[OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) sandbox integration for [Deep Agents](https://github.com/langchain-ai/deepagents).

## Quick Install

```bash
uv add langchain-opensandbox
```

```python
from opensandbox import SandboxSync

from langchain_opensandbox import OpenSandboxBackend

sandbox = SandboxSync.create("python:3.12")
backend = OpenSandboxBackend(sandbox=sandbox, timeout=300)

result = backend.execute("echo hello")
print(result.output)
```

## 🤔 What is this?

`OpenSandboxBackend` adapts the [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox)
Python SDK to the `BaseSandbox` interface used by Deep Agents, so you can run
agent-generated commands and file operations inside an OpenSandbox environment.

It implements the three sandbox primitives — `execute`, `upload_files`, and
`download_files` — on top of the OpenSandbox SDK. The higher-level file helpers
(`ls`, `read_file`, `write_file`, `glob`, `grep`) are provided by `BaseSandbox`
and built on top of `execute`.

## Configuration

`OpenSandboxBackend` wraps an existing `opensandbox.SandboxSync` instance, so it
inherits the SDK's configuration. The SDK reads connection settings from the
environment:

| Variable | Description |
| --- | --- |
| `OPENSANDBOX_DOMAIN` | Host (and optional port) of the OpenSandbox server. |
| `OPENSANDBOX_PROTOCOL` | Protocol used to reach the server (`http` or `https`). |
| `OPENSANDBOX_API_KEY` | API key, if the server requires authentication. |

## Development

```bash
uv sync
make lint            # ruff check + format --diff
make test            # unit tests (no network)
make integration_tests   # conformance suite (requires a running OpenSandbox server)
make build           # build wheel + sdist
```

The integration tests run the standard `SandboxIntegrationTests` conformance
suite from `langchain-tests`. They are skipped unless `OPENSANDBOX_DOMAIN` is
set.

## Releases & Versioning

This package follows [semantic versioning](https://semver.org/).

## Contributing

Contributions are welcome. Please open an issue or pull request on
[GitHub](https://github.com/AyushSonuu/langchain-opensandbox).

## License

Apache License 2.0. See [LICENSE](LICENSE).
