"""Webhook models — the registration record and the delivery envelope."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from stemsplit_python.models._base import BaseSDKModel
from stemsplit_python.models.jobs import (
    JobInput,
    JobOptions,
    JobOutputs,
    JobStatus,
)

WebhookEventType = Literal["job.completed", "job.failed"]


class Webhook(BaseSDKModel):
    """A registered webhook subscription.

    The ``secret`` field is only populated on the response from
    ``POST /webhooks`` — listing returns webhooks without their secrets.
    """

    id: str
    url: str
    events: list[str]
    is_active: bool = True
    fail_count: int = 0
    last_error: str | None = None
    last_called_at: datetime | None = None
    created_at: datetime
    secret: str | None = None


class WebhookListResponse(BaseSDKModel):
    """Wire shape of ``GET /webhooks``."""

    webhooks: list[Webhook]


class WebhookEventData(BaseSDKModel):
    """The ``data`` block inside a webhook delivery envelope.

    Stem-separation jobs and YouTube jobs share this envelope; YouTube
    deliveries add ``type="youtube"`` and a video-specific ``input`` block.
    """

    job_id: str
    status: JobStatus
    type: Literal["stem", "youtube"] | None = None
    input: JobInput | dict[str, Any] | None = None
    options: JobOptions | None = None
    outputs: JobOutputs | None = None
    credits_charged: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class WebhookEvent(BaseSDKModel):
    """The verified, parsed webhook delivery."""

    event: WebhookEventType
    timestamp: datetime
    data: WebhookEventData


__all__ = [
    "Webhook",
    "WebhookEvent",
    "WebhookEventData",
    "WebhookEventType",
    "WebhookListResponse",
]
