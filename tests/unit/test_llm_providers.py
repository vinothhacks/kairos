"""Direct LLM provider contracts for v0.4."""
from __future__ import annotations

import httpx
import pytest

from kairos.llm.providers.anthropic import AnthropicClient
from kairos.llm.providers.base import LLMClient, LLMError
from kairos.llm.providers.ollama import OllamaClient
from kairos.llm.providers.openai import OpenAIClient
from kairos.llm.providers.openai_compat import OpenAICompatClient
from kairos.llm.providers.stub import StubLLMClient


def test_from_env_defaults_to_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAIROS_LLM_BACKEND", raising=False)

    assert isinstance(LLMClient.from_env(), StubLLMClient)


def test_from_env_rejects_removed_llm_mcp_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAIROS_LLM_BACKEND", "mcp")

    with pytest.raises(LLMError, match="llm-mcp backend was removed"):
        LLMClient.from_env()


def test_from_env_builds_openai_compatible_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAIROS_LLM_BACKEND", "openai_compat")
    monkeypatch.setenv("KAIROS_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("KAIROS_LLM_MODEL", "local-model")

    client = LLMClient.from_env()

    assert isinstance(client, OpenAICompatClient)
    assert client.model == "local-model"


def test_ollama_client_posts_to_local_chat_api() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"message": {"content": "local answer"}})

    client = OllamaClient(
        base_url="http://ollama.local",
        model="llama3.2",
        transport=httpx.MockTransport(handler),
        backoff_base=0.0,
    )

    out = client.chatgpt_send("hello")

    assert out.text == "local answer"
    assert seen[0].url == "http://ollama.local/api/chat"
    assert seen[0].read()
    assert b'"model":"llama3.2"' in seen[0].content.replace(b" ", b"")


def test_openai_client_uses_chat_completions_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk-test"
        assert request.url == "https://api.openai.com/v1/chat/completions"
        assert b'"model":"gpt-test"' in request.content.replace(b" ", b"")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "openai answer"}}]},
        )

    client = OpenAIClient(
        api_key="sk-test",
        model="gpt-test",
        transport=httpx.MockTransport(handler),
        backoff_base=0.0,
    )

    assert client.claude_send("hello").text == "openai answer"


def test_anthropic_client_uses_messages_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "anthropic-test"
        assert request.url == "https://api.anthropic.com/v1/messages"
        assert b'"model":"claude-test"' in request.content.replace(b" ", b"")
        return httpx.Response(200, json={"content": [{"type": "text", "text": "claude answer"}]})

    client = AnthropicClient(
        api_key="anthropic-test",
        model="claude-test",
        transport=httpx.MockTransport(handler),
        backoff_base=0.0,
    )

    assert client.chatgpt_send("hello").text == "claude answer"


def test_openai_compatible_client_uses_custom_base_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer compat-key"
        assert request.url == "http://lmstudio.local/v1/chat/completions"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "compat answer"}}]},
        )

    client = OpenAICompatClient(
        base_url="http://lmstudio.local/v1",
        api_key="compat-key",
        model="local-chat",
        transport=httpx.MockTransport(handler),
        backoff_base=0.0,
    )

    assert client.chatgpt_send("hello").text == "compat answer"
