"""Models for the presigned-upload flow."""

from __future__ import annotations

from datetime import datetime

from stemsplit_python.models._base import BaseSDKModel


class UploadTicket(BaseSDKModel):
    """Response from ``POST /upload``.

    Use :attr:`upload_url` to PUT the audio bytes directly to object
    storage, then pass :attr:`upload_key` to ``POST /jobs``.
    """

    upload_url: str
    upload_key: str
    expires_at: datetime
    max_file_size_bytes: int | None = None
    max_file_size_mb: int | None = None
    content_type: str
