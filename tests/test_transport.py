"""Transport-layer tests not covered indirectly by resource tests."""

from __future__ import annotations

import io

import httpx
import pytest
import respx

from stemsplit_python._transport import Transport
from stemsplit_python.errors import APIError


@respx.mock
def test_retries_succeed_after_a_503() -> None:
    route = respx.get("https://stemsplit.io/api/v1/balance").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(
                200,
                json={
                    "balanceSeconds": 60,
                    "balanceMinutes": 1,
                    "balanceFormatted": "1 minute",
                    "updatedAt": "2026-05-21T12:00:00Z",
                },
            ),
        ]
    )
    transport = Transport(api_key="sk_live_test", max_retries=1)
    out = transport.request("GET", "/balance")
    assert out["balanceSeconds"] == 60
    assert route.call_count == 2
    transport.close()


@respx.mock
def test_429_with_retry_after_header_is_retried() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(
                200,
                json={
                    "balanceSeconds": 60,
                    "balanceMinutes": 1,
                    "balanceFormatted": "1 minute",
                    "updatedAt": "2026-05-21T12:00:00Z",
                },
            ),
        ]
    )
    transport = Transport(api_key="sk_live_test", max_retries=1)
    transport.request("GET", "/balance")
    transport.close()


@respx.mock
def test_stream_to_file_writes_to_path(tmp_path: object) -> None:
    respx.get("https://storage.example.com/x").respond(200, content=b"hello-world")
    transport = Transport(api_key="sk_live_test", max_retries=0)
    target = tmp_path / "out.bin"  # type: ignore[operator]
    written = transport.stream_to_file("https://storage.example.com/x", target)
    assert written == len(b"hello-world")
    assert target.read_bytes() == b"hello-world"
    transport.close()


@respx.mock
def test_stream_to_file_writes_to_filelike() -> None:
    respx.get("https://storage.example.com/x").respond(200, content=b"abc")
    transport = Transport(api_key="sk_live_test", max_retries=0)
    sink = io.BytesIO()
    transport.stream_to_file("https://storage.example.com/x", sink)
    assert sink.getvalue() == b"abc"
    transport.close()


@respx.mock
def test_stream_to_file_raises_on_404() -> None:
    respx.get("https://storage.example.com/missing").respond(404)
    transport = Transport(api_key="sk_live_test", max_retries=0)
    with pytest.raises(APIError):
        transport.stream_to_file("https://storage.example.com/missing", io.BytesIO())
    transport.close()


@respx.mock
def test_put_to_presigned_url_does_not_send_auth_header() -> None:
    route = respx.put("https://storage.example.com/presign").respond(200)
    transport = Transport(api_key="sk_live_secret", max_retries=0)
    transport.put_to_presigned_url(
        "https://storage.example.com/presign", b"audio", "audio/mpeg", content_length=5
    )
    request = route.calls.last.request
    assert "Authorization" not in request.headers
    assert request.headers["Content-Type"] == "audio/mpeg"
    transport.close()


@respx.mock
def test_idempotency_key_forwarded_as_header() -> None:
    route = respx.post("https://stemsplit.io/api/v1/jobs").respond(
        201,
        json={
            "id": "job_1",
            "status": "PENDING",
            "progress": 0,
            "createdAt": "2026-05-21T12:00:00Z",
        },
    )
    transport = Transport(api_key="sk_live_test", max_retries=0)
    transport.request(
        "POST",
        "/jobs",
        json_body={"sourceUrl": "https://example.com/song.mp3"},
        idempotency_key="abc-123",
        retry_safe=True,
    )
    assert route.calls.last.request.headers["Idempotency-Key"] == "abc-123"
    transport.close()
