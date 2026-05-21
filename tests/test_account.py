"""Account / balance endpoint."""

from __future__ import annotations

import httpx
import respx

from stemsplit_python import StemSplit


@respx.mock
def test_get_balance() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").mock(
        return_value=httpx.Response(
            200,
            json={
                "balanceSeconds": 300,
                "balanceMinutes": 5,
                "balanceFormatted": "5 minutes",
                "updatedAt": "2026-05-21T12:00:00Z",
            },
            headers={
                "x-ratelimit-limit": "60",
                "x-ratelimit-remaining": "59",
                "x-ratelimit-reset": "1700000060",
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    balance = client.account.balance()
    assert balance.balance_seconds == 300
    assert balance.balance_minutes == 5
    assert balance.balance_formatted == "5 minutes"

    rate = client.last_rate_limit
    assert rate is not None
    assert rate.limit == 60
    assert rate.remaining == 59
    assert rate.reset_at == 1700000060


@respx.mock
def test_get_alias_returns_balance() -> None:
    respx.get("https://stemsplit.io/api/v1/balance").respond(
        200,
        json={
            "balanceSeconds": 0,
            "balanceMinutes": 0,
            "balanceFormatted": "0 seconds",
            "updatedAt": "2026-05-21T12:00:00Z",
        },
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    assert client.account.get().balance_seconds == 0
