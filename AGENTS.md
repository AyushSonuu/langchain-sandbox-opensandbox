# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this package is

`langchain-sandbox-opensandbox` is a partner integration package. It provides
`OpenSandboxBackend`, an adapter that lets [Deep Agents](https://github.com/langchain-ai/deepagents)
run commands and file operations inside an [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox)
environment.

The package is a thin adapter. It bridges two independent interfaces:

- **OpenSandbox SDK** (`opensandbox.SandboxSync`) — the sandbox runtime.
- **Deep Agents** (`deepagents.backends.sandbox.BaseSandbox`) — the interface
  agents call.

`OpenSandboxBackend` implements only the three required primitives:

| `BaseSandbox` method | OpenSandbox SDK call |
| --- | --- |
| `execute(command)` | `sandbox.commands.run(command, opts=...)` |
| `upload_files([(path, bytes)])` | `sandbox.files.write_files([WriteEntry(...)])` |
| `download_files([path])` | `sandbox.files.read_bytes(path)` |
| `id` | `sandbox.id` |

Everything else (`ls`, `read_file`, `write_file`, `glob`, `grep`) is inherited
from `BaseSandbox` and built on `execute`. **Do not re-implement those.**

## Project layout

```
langchain_opensandbox/
  __init__.py     # public exports
  _version.py     # __version__
  sandbox.py      # OpenSandboxBackend
tests/
  unit_tests/     # mock-based, no network
  integration_tests/  # SandboxIntegrationTests conformance suite
```

## Commands

```bash
uv sync
make lint                # ruff check + format --diff
make format              # ruff format + check --fix
make test                # unit tests (sockets disabled)
make integration_tests   # conformance suite (needs a running OpenSandbox server)
make build               # build wheel + sdist
```

## Conventions

- Python `>=3.11,<4.0`.
- Ruff for lint and format; `select = ["ALL"]`. Keep it clean.
- Google-style docstrings on public methods.
- No relative imports.
- Unit tests must not touch the network (`make test` disables sockets).
- Integration tests are skipped unless `OPENSANDBOX_DOMAIN` is set.
- Conventional Commits for commit messages (`feat:`, `fix:`, `docs:`, `test:`,
  `chore:`).

## Do not

- Do not commit secrets. `.env` files are gitignored.
- Do not add dependencies beyond `deepagents` and `opensandbox` in the runtime
  dependency set without a clear need.
- Do not widen the adapter's surface — keep it to the three primitives plus
  `id`.
