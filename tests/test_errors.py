"""Error-status mapping and bonus fields on rate-limit / insufficient-credits."""

from __future__ import annotations

import httpx
import pytest
import respx

from stemsplit_python import (
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    InsufficientCreditsError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    StemSplit,
)
from stemsplit_python._transport import Transport


def _make_client() -> StemSplit:
    return StemSplit(api_key="sk_live_test", base_url="https://stemsplit.io/api/v1", max_retries=0)


@respx.mock
def test_400_bad_request_maps_to_BadRequestError() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").respond(
        400, json={"error": {"code": "FILE_TOO_LARGE", "message": "File exceeds 50MB"}}
    )
    client = _make_client()
    with pytest.raises(BadRequestError) as exc:
        client.account.balance()
    assert exc.value.status_code == 400
    assert exc.value.code == "FILE_TOO_LARGE"
    assert "File exceeds 50MB" in str(exc.value)


@respx.mock
def test_401_maps_to_AuthenticationError() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").respond(
        401, json={"error": {"code": "MISSING_API_KEY", "message": "Missing API key."}}
    )
    with pytest.raises(AuthenticationError):
        _make_client().account.balance()


@respx.mock
def test_402_carries_insufficient_credits_fields() -> None:
    respx.post("https://stemsplit.io/api/v1/jobs").respond(
        402,
        json={
            "error": {
                "code": "INSUFFICIENT_CREDITS",
                "message": "Not enough credits",
                "requiredSeconds": 180,
                "purchaseUrl": "https://stemsplit.io/pricing",
            }
        },
    )
    client = _make_client()
    with pytest.raises(InsufficientCreditsError) as exc:
        client.jobs.create(source_url="https://example.com/song.mp3")
    assert exc.value.required_seconds == 180
    assert exc.value.purchase_url == "https://stemsplit.io/pricing"


@respx.mock
def test_403_maps_to_PermissionDeniedError() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").respond(
        403, json={"error": {"code": "API_KEY_REVOKED", "message": "Key was revoked"}}
    )
    with pytest.raises(PermissionDeniedError) as exc:
        _make_client().account.balance()
    assert exc.value.code == "API_KEY_REVOKED"


@respx.mock
def test_404_maps_to_NotFoundError() -> None:
    respx.get("https://stemsplit.io/api/v1/jobs/missing").respond(
        404, json={"error": {"code": "JOB_NOT_FOUND", "message": "Job not found"}}
    )
    with pytest.raises(NotFoundError):
        _make_client().jobs.get("missing")


@respx.mock
def test_429_carries_rate_limit_headers() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").mock(
        return_value=httpx.Response(
            429,
            headers={
                "retry-after": "30",
                "x-ratelimit-limit": "60",
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1700000000",
            },
            json={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Slow down"}},
        )
    )
    with pytest.raises(RateLimitError) as exc:
        _make_client().account.balance()
    assert exc.value.retry_after == 30
    assert exc.value.limit == 60
    assert exc.value.remaining == 0


@respx.mock
def test_500_maps_to_InternalServerError() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").respond(
        500, json={"error": {"code": "INTERNAL", "message": "boom"}}
    )
    with pytest.raises(InternalServerError):
        _make_client().account.balance()


@respx.mock
def test_unknown_status_uses_APIStatusError() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").respond(
        418, json={"error": {"code": "TEAPOT", "message": "I am a teapot"}}
    )
    with pytest.raises(APIStatusError) as exc:
        _make_client().account.balance()
    assert exc.value.status_code == 418


@respx.mock
def test_retries_exhausted_then_raises() -> None:
    """With max_retries=2 we should see 3 attempts total before giving up."""

    route = respx.get("https://stemsplit.io/api/v1/balance").respond(503)
    transport = Transport(api_key="sk_live_test", max_retries=2)
    with pytest.raises(InternalServerError):
        transport.request("GET", "/balance")
    assert route.call_count == 3
    transport.close()
