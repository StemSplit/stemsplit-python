"""Models for the ``/jobs`` resource and stem-separation job lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from stemsplit_python.models._base import BaseSDKModel, ListPagination

JobStatus = Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED", "EXPIRED"]
JobOutputType = Literal["VOCALS", "INSTRUMENTAL", "BOTH", "FOUR_STEMS", "SIX_STEMS"]
JobQuality = Literal["FAST", "BALANCED", "BEST"]
OutputFormat = Literal["WAV", "MP3", "FLAC"]


class JobInput(BaseSDKModel):
    """Input metadata captured when the job was created."""

    file_name: str | None = None
    duration_seconds: int | None = None
    file_size_bytes: int | None = None


class JobOptions(BaseSDKModel):
    """The job-creation options the user picked."""

    output_type: str | None = None
    quality: str | None = None
    output_format: str | None = None


class AudioMetadata(BaseSDKModel):
    """Optional audio analysis attached to a completed job.

    Both fields can be ``None`` if the analysis didn't run or the file was
    too short. ``key`` is a free-form string like ``"Gm"`` or ``"C#"``.

    .. note::
       The live OpenAPI 3.1 spec at ``/api/v1/openapi`` does not yet
       describe this object — it is documented in the developer guide and
       returned by the live API. The SDK models it from the docs.
    """

    bpm: float | None = None
    key: str | None = None


class JobOutputFile(BaseSDKModel):
    """A single downloadable stem.

    Presigned URLs are valid for ~1 hour. To refresh, ``GET /jobs/{id}``.
    """

    url: str
    expires_at: datetime


class JobOutputs(BaseSDKModel):
    """Per-stem download links for a completed job.

    Which keys are populated depends on the ``outputType`` the job was
    created with. A six-stem job populates all five musical stems; a
    YouTube job adds ``full_audio``.
    """

    vocals: JobOutputFile | None = None
    instrumental: JobOutputFile | None = None
    drums: JobOutputFile | None = None
    bass: JobOutputFile | None = None
    other: JobOutputFile | None = None
    piano: JobOutputFile | None = None
    guitar: JobOutputFile | None = None
    full_audio: JobOutputFile | None = Field(default=None, alias="fullAudio")

    def as_dict(self) -> dict[str, JobOutputFile]:
        """Return ``{stem_name: JobOutputFile}`` skipping unset stems."""

        out: dict[str, JobOutputFile] = {}
        for stem in (
            "vocals",
            "instrumental",
            "drums",
            "bass",
            "other",
            "piano",
            "guitar",
            "full_audio",
        ):
            value = getattr(self, stem)
            if value is not None:
                out[stem] = value
        return out


class Job(BaseSDKModel):
    """A stem-separation job — the headline resource.

    ``Job`` is a pure data record; the live :class:`stemsplit_python.JobHandle`
    wrapper adds ``.wait()`` / ``.refresh()`` / ``.download_all()`` ergonomics.
    """

    id: str
    status: JobStatus
    progress: int = 0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    input: JobInput | None = None
    options: JobOptions | None = None
    outputs: JobOutputs | None = None
    audio_metadata: AudioMetadata | None = None
    credits_required: int | None = None
    credits_charged: int | None = None
    estimated_seconds: int | None = None
    error_message: str | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class JobListResponse(BaseSDKModel):
    """Wire shape of ``GET /jobs``."""

    jobs: list[Job]
    pagination: ListPagination


__all__ = [
    "AudioMetadata",
    "Job",
    "JobInput",
    "JobListResponse",
    "JobOptions",
    "JobOutputFile",
    "JobOutputType",
    "JobOutputs",
    "JobQuality",
    "JobStatus",
    "OutputFormat",
]
