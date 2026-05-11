"""KAI-015 / KAI-017 integration tests for MCPLLMClient.

Uses httpx.MockTransport to simulate llm-mcp without a network server.
Covers retries, backoff, MCPUnreachable, and 5xx classification.
"""
from __future__ import annotations

import httpx
import pytest

from kairos.llm.mcp_client import LLMError, MCPLLMClient, MCPUnreachable

pytestmark = pytest.mark.integration


def _fake_app_for(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Return a MockTransport that pops one response from the list per request."""
    iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        try:
            return next(iterator)
        except StopIteration:
            return httpx.Response(500, text="mock exhausted")

    return httpx.MockTransport(handler)


def _make_client(transport: httpx.MockTransport) -> MCPLLMClient:
    client = MCPLLMClient(base_url="http://mock", timeout_s=1.0, backoff_base=0.0)
    client._transport = transport
    return client


def test_mcp_client_returns_reply_on_200() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(200, json={"reply": "hi"}),
        ]
    )
    client = _make_client(transport)
    out = client._post("ping", {})
    assert out["reply"] == "hi"


def test_mcp_client_retries_on_5xx_then_succeeds() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
            httpx.Response(200, json={"reply": "ok"}),
        ]
    )
    client = _make_client(transport)
    out = client._post("chatgpt_send", {"message": "hi"})
    assert out["reply"] == "ok"


def test_mcp_client_raises_after_max_retries_on_5xx() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
        ]
    )
    client = _make_client(transport)
    with pytest.raises(LLMError):
        client._post("chatgpt_send", {"message": "hi"})


def test_mcp_client_does_not_retry_on_4xx() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(400, text="bad request"),
        ]
    )
    client = _make_client(transport)
    with pytest.raises(LLMError):
        client._post("chatgpt_send", {"message": "hi"})


def test_mcp_client_unreachable_raises_specific_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    client = _make_client(httpx.MockTransport(boom))
    with pytest.raises(MCPUnreachable):
        client._post("ping", {})


def test_mcp_client_rejects_non_json_body() -> None:
    transport = _fake_app_for(
        [httpx.Response(200, text="this is not JSON")]
    )
    client = _make_client(transport)
    with pytest.raises(LLMError):
        client._post("ping", {})
