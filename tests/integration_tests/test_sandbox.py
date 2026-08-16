from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from langchain_tests.integration_tests import SandboxIntegrationTests
from opensandbox import SandboxSync

from langchain_opensandbox import OpenSandboxBackend

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENSANDBOX_DOMAIN"),
    reason="OPENSANDBOX_DOMAIN not set; skipping OpenSandbox integration tests",
)


class TestOpenSandboxStandard(SandboxIntegrationTests):
    """Run the standard sandbox conformance suite against OpenSandbox."""

    @pytest.fixture(scope="class")
    def sandbox(self) -> Iterator[OpenSandboxBackend]:
        sb = SandboxSync.create("python:3.12")
        try:
            yield OpenSandboxBackend(sandbox=sb, timeout=120)
        finally:
            sb.kill()
