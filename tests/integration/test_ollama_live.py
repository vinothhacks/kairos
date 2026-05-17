"""Optional live Ollama smoke for the direct local backend."""
from __future__ import annotations

import os

import pytest

from kairos.llm.providers.ollama import OllamaClient

pytestmark = [pytest.mark.integration, pytest.mark.live]


def test_live_ollama_backend_replies_when_enabled() -> None:
    if os.environ.get("KAIROS_LIVE") != "ollama":
        pytest.skip("set KAIROS_LIVE=ollama to run the live Ollama smoke")

    client = OllamaClient(timeout_s=30.0)
    assert client.ping()

    out = client.chatgpt_send("Reply with exactly: kairos-ollama-ok")
    assert out.text.strip()
