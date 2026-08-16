from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from langchain_tests.integration_tests import SandboxIntegrationTests
from opensandbox import SandboxSync
from opensandbox.config.connection_sync import ConnectionConfigSync

from langchain_opensandbox import OpenSandboxBackend

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENSANDBOX_DOMAIN"),
    reason="OPENSANDBOX_DOMAIN not set; skipping OpenSandbox integration tests",
)


class TestOpenSandboxStandard(SandboxIntegrationTests):
    """Run the standard sandbox conformance suite against OpenSandbox.

    The suite connects to a real OpenSandbox server configured via environment:

    - ``OPENSANDBOX_DOMAIN`` (required) -- management API host.
    - ``OPENSANDBOX_API_KEY`` (optional) -- API key for authentication.
    - ``OPENSANDBOX_PROTOCOL`` (optional) -- ``http`` (default) or ``https``.

    The SDK does not read these itself, so the fixture wires them into a
    ``ConnectionConfigSync``. Without ``OPENSANDBOX_DOMAIN`` the whole module is
    skipped (see ``pytestmark`` above).
    """

    @pytest.fixture(scope="class")
    def sandbox(self) -> Iterator[OpenSandboxBackend]:
        connection_config = ConnectionConfigSync(
            domain=os.environ["OPENSANDBOX_DOMAIN"],
            api_key=os.environ.get("OPENSANDBOX_API_KEY"),
            protocol=os.environ.get("OPENSANDBOX_PROTOCOL", "http"),
        )
        sb = SandboxSync.create("python:3.12", connection_config=connection_config)
        try:
            yield OpenSandboxBackend(sandbox=sb, timeout=120)
        finally:
            sb.kill()
