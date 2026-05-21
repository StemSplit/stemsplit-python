"""Models for ``/youtube-jobs``.

The YouTube endpoints are documented in the developer guide but do not yet
appear in the live OpenAPI spec — these models are based on the docs and
the live JSON shape we observe.
"""

from __future__ import annotations

from datetime import datetime

from stemsplit_python.models._base import BaseSDKModel, ListPagination
from stemsplit_python.models.jobs import (
    AudioMetadata,
    JobOptions,
    JobOutputs,
    JobStatus,
)


class YouTubeJob(BaseSDKModel):
    """A YouTube stem-separation job.

    Like :class:`stemsplit_python.models.Job` but with extra video metadata.
    """

    id: str
    status: JobStatus
    progress: int = 0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    video_id: str | None = None
    video_title: str | None = None
    video_duration: int | None = None
    video_thumbnail: str | None = None
    channel_name: str | None = None
    youtube_url: str | None = None

    options: JobOptions | None = None
    outputs: JobOutputs | None = None
    audio_metadata: AudioMetadata | None = None
    credits_required: int | None = None
    credits_charged: int | None = None
    estimated_seconds: int | None = None
    error_message: str | None = None
    expires_at: datetime | None = None


class YouTubeJobListResponse(BaseSDKModel):
    """Wire shape of ``GET /youtube-jobs``."""

    jobs: list[YouTubeJob]
    pagination: ListPagination


__all__ = ["YouTubeJob", "YouTubeJobListResponse"]
