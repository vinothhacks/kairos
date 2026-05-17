"""KAI-017 integration tests for direct provider HTTP retry behavior.

Uses httpx.MockTransport to simulate provider APIs without a network server.
Covers retries, backoff, provider unreachable, and 5xx classification.
"""
from __future__ import annotations

import httpx
import pytest

from kairos.llm.providers._http import RetryingHTTPClient
from kairos.llm.providers.base import LLMError, MCPUnreachable

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


def _make_client(transport: httpx.MockTransport) -> RetryingHTTPClient:
    return RetryingHTTPClient(
        base_url="http://mock",
        timeout_s=1.0,
        backoff_base=0.0,
        transport=transport,
    )


def test_http_client_returns_dict_on_200() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(200, json={"reply": "hi"}),
        ]
    )
    client = _make_client(transport)
    out = client.request_json("POST", "/ping", json_body={})
    assert out["reply"] == "hi"


def test_http_client_retries_on_5xx_then_succeeds() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
            httpx.Response(200, json={"reply": "ok"}),
        ]
    )
    client = _make_client(transport)
    out = client.request_json("POST", "/chat", json_body={"message": "hi"})
    assert out["reply"] == "ok"


def test_http_client_raises_after_max_retries_on_5xx() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
            httpx.Response(503, text="busy"),
        ]
    )
    client = _make_client(transport)
    with pytest.raises(LLMError):
        client.request_json("POST", "/chat", json_body={"message": "hi"})


def test_http_client_does_not_retry_on_4xx() -> None:
    transport = _fake_app_for(
        [
            httpx.Response(400, text="bad request"),
        ]
    )
    client = _make_client(transport)
    with pytest.raises(LLMError):
        client.request_json("POST", "/chat", json_body={"message": "hi"})


def test_http_client_unreachable_raises_specific_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    client = _make_client(httpx.MockTransport(boom))
    with pytest.raises(MCPUnreachable):
        client.request_json("POST", "/ping", json_body={})


def test_http_client_rejects_non_json_body() -> None:
    transport = _fake_app_for(
        [httpx.Response(200, text="this is not JSON")]
    )
    client = _make_client(transport)
    with pytest.raises(LLMError):
        client.request_json("POST", "/ping", json_body={})
