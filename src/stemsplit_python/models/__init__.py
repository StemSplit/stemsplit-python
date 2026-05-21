"""Typed models for every shape the StemSplit API returns.

All models are immutable (``frozen=True``), accept extra fields without
crashing (``extra="allow"``) and use snake_case Python attributes aliased to
the camelCase wire names. The status / quality / format / event-type fields
are :class:`typing.Literal` unions, not enums, per project convention.
"""

from __future__ import annotations

from stemsplit_python.models._base import BaseSDKModel, ListPagination
from stemsplit_python.models.account import Balance
from stemsplit_python.models.jobs import (
    AudioMetadata,
    Job,
    JobInput,
    JobListResponse,
    JobOptions,
    JobOutputFile,
    JobOutputs,
    JobOutputType,
    JobQuality,
    JobStatus,
    OutputFormat,
)
from stemsplit_python.models.uploads import UploadTicket
from stemsplit_python.models.webhooks import (
    Webhook,
    WebhookEvent,
    WebhookEventData,
    WebhookEventType,
    WebhookListResponse,
)
from stemsplit_python.models.youtube_jobs import YouTubeJob, YouTubeJobListResponse

__all__ = [
    "AudioMetadata",
    "Balance",
    "BaseSDKModel",
    "Job",
    "JobInput",
    "JobListResponse",
    "JobOptions",
    "JobOutputFile",
    "JobOutputType",
    "JobOutputs",
    "JobQuality",
    "JobStatus",
    "ListPagination",
    "OutputFormat",
    "UploadTicket",
    "Webhook",
    "WebhookEvent",
    "WebhookEventData",
    "WebhookEventType",
    "WebhookListResponse",
    "YouTubeJob",
    "YouTubeJobListResponse",
]
