# langchain-sandbox-opensandbox

[![PyPI - Version](https://img.shields.io/pypi/v/langchain-sandbox-opensandbox?label=%20)](https://pypi.org/project/langchain-sandbox-opensandbox/#history)
[![PyPI - License](https://img.shields.io/pypi/l/langchain-sandbox-opensandbox)](https://opensource.org/licenses/Apache-2.0)
[![PyPI - Downloads](https://img.shields.io/pepy/dt/langchain-sandbox-opensandbox)](https://pypistats.org/packages/langchain-sandbox-opensandbox)

[OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) sandbox integration for [Deep Agents](https://github.com/langchain-ai/deepagents).

## Quick Install

```bash
uv add langchain-sandbox-opensandbox
```

> The distribution is published as `langchain-sandbox-opensandbox`, but the
> import package is `langchain_opensandbox`.

```python
from opensandbox import SandboxSync

from langchain_opensandbox import OpenSandboxBackend

sandbox = SandboxSync.create("python:3.12")
backend = OpenSandboxBackend(sandbox=sandbox, timeout=300)

result = backend.execute("echo hello")
print(result.output)
```

## Using it with Deep Agents

Pass the backend to a Deep Agent so the agent's file and shell tools run
inside the OpenSandbox environment instead of on the host:

```python
from deepagents import create_deep_agent
from opensandbox import SandboxSync

from langchain_opensandbox import OpenSandboxBackend

# 1. Spin up a sandbox and wrap it.
sandbox = SandboxSync.create("python:3.12")
backend = OpenSandboxBackend(sandbox=sandbox, timeout=300)

# 2. Hand the backend to the agent. Every ls / read_file / write_file /
#    glob / grep / execute the agent performs is now sandboxed.
agent = create_deep_agent(
    tools=[],
    system_prompt="You are a coding assistant. Use the sandbox to run code.",
    backend=backend,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Create hello.py and run it."}]}
)
print(result["messages"][-1].content)

# 3. Tear the sandbox down when you're done.
sandbox.kill()
```

The higher-level file helpers the agent calls (`ls`, `read_file`,
`write_file`, `glob`, `grep`) are provided by `BaseSandbox` and built on top
of the three primitives this adapter implements (`execute`, `upload_files`,
`download_files`).

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
inherits whatever connection you configured on the SDK. To point at a specific
server, build a `ConnectionConfigSync` and pass it to `SandboxSync.create`:

```python
from opensandbox import SandboxSync
from opensandbox.config.connection_sync import ConnectionConfigSync

from langchain_opensandbox import OpenSandboxBackend

connection = ConnectionConfigSync(
    domain="127.0.0.1:8080",  # host (and optional port) of the server
    protocol="http",          # "http" or "https"
    api_key="my-api-key",     # if the server requires authentication
)
sandbox = SandboxSync.create("python:3.12", connection_config=connection)
backend = OpenSandboxBackend(sandbox=sandbox)
```

## Running a local OpenSandbox server

The integration tests (and the snippets above) need a reachable OpenSandbox
server. You can run one locally with Docker:

```bash
# Requires Docker to be running.
uvx opensandbox-server init-config ./os-sandbox.toml --example docker
uvx opensandbox-server --config ./os-sandbox.toml
```

This starts the management API on `127.0.0.1:8080`. Set an `api_key` in the
generated config if you want authentication; otherwise the server starts in
insecure mode. Then point the SDK at it with `domain="127.0.0.1:8080"` and
`protocol="http"` as shown above.

## Development

```bash
uv sync
make lint            # ruff check + format --diff
make test            # unit tests (no network)
make integration_tests   # conformance suite (requires a running OpenSandbox server)
make build           # build wheel + sdist
```

## Conformance

The integration tests run the standard `SandboxIntegrationTests` conformance
suite from [`langchain-tests`](https://pypi.org/project/langchain-tests/) — the
same suite every Deep Agents sandbox backend is validated against. It exercises
`execute`, file upload/download, and all the inherited helpers (`ls`,
`read_file`, `write_file`, `glob`, `grep`) with real I/O, including large
payloads, escaped content, error handling, and both the sync and async paths.

This adapter passes the **full suite (86/86)** against a live OpenSandbox
server — no mocks, no skips:

```bash
OPENSANDBOX_DOMAIN=127.0.0.1:8080 \
OPENSANDBOX_PROTOCOL=http \
OPENSANDBOX_API_KEY=<your-key> \
make integration_tests
```

The suite is skipped automatically unless `OPENSANDBOX_DOMAIN` is set, so
`make test` stays offline and fast.

## Releases & Versioning

This package follows [semantic versioning](https://semver.org/).

## Contributing

Contributions are welcome. Please open an issue or pull request on
[GitHub](https://github.com/AyushSonuu/langchain-sandbox-opensandbox).

## License

Apache License 2.0. See [LICENSE](LICENSE).
