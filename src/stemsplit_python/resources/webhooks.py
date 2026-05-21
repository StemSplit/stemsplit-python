"""Webhook CRUD."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from stemsplit_python.models.webhooks import Webhook, WebhookListResponse

if TYPE_CHECKING:
    from stemsplit_python._transport import Transport


class WebhooksResource:
    """``POST /webhooks`` / ``GET /webhooks`` / ``DELETE /webhooks/{id}``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def create(
        self,
        *,
        url: str,
        events: Sequence[str] | None = None,
        idempotency_key: str | None = None,
    ) -> Webhook:
        """Register a webhook subscription.

        The returned :class:`Webhook` carries a ``secret`` field — capture it
        now, the API never returns it again.
        """

        body: dict[str, object] = {"url": url}
        if events is not None:
            body["events"] = list(events)
        data = self._transport.request(
            "POST",
            "/webhooks",
            json_body=body,
            idempotency_key=idempotency_key,
            retry_safe=True,
        )
        return Webhook.model_validate(data)

    def list(self) -> list[Webhook]:
        """List every webhook subscription on the account.

        Returns the webhooks directly (the wire shape wraps them in
        ``{"webhooks": [...]}``; we unwrap so callers can iterate).
        """

        data = self._transport.request("GET", "/webhooks")
        return WebhookListResponse.model_validate(data).webhooks

    def delete(self, webhook_id: str) -> bool:
        """Delete a webhook subscription. Returns ``True`` on success."""

        data = self._transport.request("DELETE", f"/webhooks/{webhook_id}")
        if isinstance(data, dict):
            return bool(data.get("deleted", True))
        return True


__all__ = ["WebhooksResource"]
