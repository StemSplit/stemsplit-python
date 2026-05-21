"""Webhook CRUD resource."""

from __future__ import annotations

import httpx
import respx

from stemsplit_python import StemSplit


@respx.mock
def test_create_webhook_returns_secret() -> None:
    respx.post("https://stemsplit.io/api/v1/webhooks").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "wh_abc",
                "url": "https://example.com/wh",
                "events": ["job.completed", "job.failed"],
                "secret": "whsec_super_secret",
                "isActive": True,
                "createdAt": "2026-05-21T12:00:00Z",
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    hook = client.webhooks.create(url="https://example.com/wh")
    assert hook.id == "wh_abc"
    assert hook.secret == "whsec_super_secret"


@respx.mock
def test_list_webhooks_returns_list() -> None:
    respx.get("https://stemsplit.io/api/v1/webhooks").mock(
        return_value=httpx.Response(
            200,
            json={
                "webhooks": [
                    {
                        "id": "wh_abc",
                        "url": "https://example.com/wh",
                        "events": ["job.completed", "job.failed"],
                        "isActive": True,
                        "failCount": 0,
                        "createdAt": "2026-05-21T12:00:00Z",
                    },
                ]
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    items = client.webhooks.list()
    assert len(items) == 1
    assert items[0].secret is None


@respx.mock
def test_delete_webhook_returns_true() -> None:
    respx.delete("https://stemsplit.io/api/v1/webhooks/wh_abc").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    assert client.webhooks.delete("wh_abc") is True
