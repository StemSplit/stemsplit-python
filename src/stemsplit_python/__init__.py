"""Official Python SDK for the StemSplit hosted stem-separation API.

Get an API key at https://stemsplit.io/app/settings/api, then::

    from pathlib import Path
    from stemsplit_python import StemSplit

    client = StemSplit(api_key="sk_live_...")  # or set STEMSPLIT_API_KEY
    job = client.jobs.create(audio=Path("song.mp3"), output_type="BOTH").wait()
    job.download_all("./out/")

Webhook signature verification lives in :mod:`stemsplit_python.webhooks`.
"""

from stemsplit_python import webhooks
from stemsplit_python._transport import RateLimit
from stemsplit_python._version import __version__
from stemsplit_python.client import AsyncStemSplit, StemSplit
from stemsplit_python.errors import (
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InsufficientCreditsError,
    InternalServerError,
    JobExpiredError,
    JobFailedError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SignatureVerificationError,
    StemSplitError,
    UnprocessableEntityError,
)
from stemsplit_python.models import (
    AudioMetadata,
    Balance,
    Job,
    JobInput,
    JobOptions,
    JobOutputFile,
    JobOutputs,
    JobOutputType,
    JobQuality,
    JobStatus,
    OutputFormat,
    UploadTicket,
    Webhook,
    WebhookEvent,
    WebhookEventData,
    WebhookEventType,
    YouTubeJob,
)
from stemsplit_python.resources.jobs import JobHandle
from stemsplit_python.resources.youtube_jobs import YouTubeJobHandle

__all__ = [
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncStemSplit",
    "AudioMetadata",
    "AuthenticationError",
    "BadRequestError",
    "Balance",
    "ConflictError",
    "InsufficientCreditsError",
    "InternalServerError",
    "Job",
    "JobExpiredError",
    "JobFailedError",
    "JobHandle",
    "JobInput",
    "JobOptions",
    "JobOutputFile",
    "JobOutputType",
    "JobOutputs",
    "JobQuality",
    "JobStatus",
    "NotFoundError",
    "OutputFormat",
    "PermissionDeniedError",
    "RateLimit",
    "RateLimitError",
    "SignatureVerificationError",
    "StemSplit",
    "StemSplitError",
    "UnprocessableEntityError",
    "UploadTicket",
    "Webhook",
    "WebhookEvent",
    "WebhookEventData",
    "WebhookEventType",
    "YouTubeJob",
    "YouTubeJobHandle",
    "__version__",
    "webhooks",
]
