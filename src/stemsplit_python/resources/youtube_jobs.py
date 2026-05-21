"""YouTube stem-separation jobs (``/youtube-jobs``).

Same lifecycle as :mod:`stemsplit_python.resources.jobs` — only the input
shape differs (``youtubeUrl`` instead of an upload).

.. note::
   These endpoints are documented in the developer guide but do not yet
   appear in the live OpenAPI spec. The SDK speaks them anyway because
   they're part of the official, supported, public API.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from stemsplit_python.errors import JobExpiredError, JobFailedError
from stemsplit_python.models.jobs import (
    JobOutputs,
    JobQuality,
    JobStatus,
    OutputFormat,
)
from stemsplit_python.models.youtube_jobs import (
    YouTubeJob,
    YouTubeJobListResponse,
)

if TYPE_CHECKING:
    from stemsplit_python._transport import Transport


class YouTubeJobHandle:
    """A live :class:`YouTubeJob` with the convenience helpers attached."""

    def __init__(self, job: YouTubeJob, resource: YouTubeJobsResource) -> None:
        self._job = job
        self._resource = resource

    @property
    def job(self) -> YouTubeJob:
        return self._job

    @property
    def id(self) -> str:
        return self._job.id

    @property
    def status(self) -> JobStatus:
        return self._job.status

    @property
    def progress(self) -> int:
        return self._job.progress

    @property
    def video_title(self) -> str | None:
        return self._job.video_title

    @property
    def outputs(self) -> JobOutputs | None:
        return self._job.outputs

    @property
    def is_terminal(self) -> bool:
        return self._job.status in {"COMPLETED", "FAILED", "EXPIRED"}

    def __repr__(self) -> str:
        return (
            f"YouTubeJobHandle(id={self._job.id!r}, status={self._job.status!r}, "
            f"progress={self._job.progress})"
        )

    def refresh(self) -> YouTubeJob:
        self._job = self._resource._fetch_one(self._job.id)
        return self._job

    def iter_progress(
        self,
        *,
        poll_interval: float = 5.0,
        timeout: float | None = 600.0,
    ) -> Iterator[YouTubeJob]:
        start = time.monotonic()
        yield self._job
        while not self.is_terminal:
            if timeout is not None and time.monotonic() - start >= timeout:
                return
            time.sleep(poll_interval)
            self.refresh()
            yield self._job

    def wait(
        self,
        *,
        timeout: float = 900.0,
        poll_interval: float = 5.0,
    ) -> YouTubeJob:
        """Block until the job finishes; raise on FAILED / EXPIRED / timeout."""

        for snapshot in self.iter_progress(poll_interval=poll_interval, timeout=timeout):
            if snapshot.status == "COMPLETED":
                return snapshot
            if snapshot.status == "FAILED":
                raise JobFailedError(snapshot.id, snapshot.error_message)
            if snapshot.status == "EXPIRED":
                raise JobExpiredError(snapshot.id)
        raise TimeoutError(
            f"Timed out waiting for YouTube job {self._job.id} after {timeout}s "
            f"(last status: {self._job.status})."
        )

    def download_all(
        self,
        directory: str | Path,
        *,
        prefix: str | None = None,
    ) -> dict[str, Path]:
        outputs = self._job.outputs
        if outputs is None:
            raise RuntimeError(
                f"YouTube job {self._job.id} has no outputs yet (status={self._job.status}). "
                "Call .wait() before downloading."
            )
        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        prefix = prefix or ""
        written: dict[str, Path] = {}
        for stem, output in outputs.as_dict().items():
            ext = _ext_from_url(output.url)
            dest = target_dir / f"{prefix}{stem}{ext}"
            self._resource._transport.stream_to_file(output.url, dest)
            written[stem] = dest
        return written


class YouTubeJobsResource:
    """``client.youtube_jobs`` — create, get, list, iter_all."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def create(
        self,
        *,
        url: str | None = None,
        youtube_url: str | None = None,
        quality: JobQuality | None = None,
        output_format: OutputFormat | None = None,
        metadata: dict[str, Any] | None = None,
        callback_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> YouTubeJobHandle:
        """Create a YouTube stem-separation job.

        ``url`` and ``youtube_url`` are aliases — pass either. The SDK uses
        ``url`` to match the brief and forwards ``youtubeUrl`` on the wire.
        """

        resolved_url = url or youtube_url
        if not resolved_url:
            raise ValueError("Pass url='https://youtube.com/watch?v=…' to create a YouTube job.")
        body: dict[str, Any] = {"youtubeUrl": resolved_url}
        if quality is not None:
            body["quality"] = quality
        if output_format is not None:
            body["outputFormat"] = output_format
        if metadata is not None:
            body["metadata"] = metadata
        if callback_url is not None:
            body["callbackUrl"] = callback_url

        data = self._transport.request(
            "POST",
            "/youtube-jobs",
            json_body=body,
            idempotency_key=idempotency_key,
            retry_safe=True,
        )
        return YouTubeJobHandle(YouTubeJob.model_validate(data), self)

    def get(self, job_id: str) -> YouTubeJobHandle:
        return YouTubeJobHandle(self._fetch_one(job_id), self)

    def list(
        self,
        *,
        limit: int | None = 20,
        offset: int | None = 0,
        status: JobStatus | None = None,
    ) -> list[YouTubeJobHandle]:
        params: dict[str, Any] = {"limit": limit, "offset": offset, "status": status}
        data = self._transport.request("GET", "/youtube-jobs", params=params)
        page = YouTubeJobListResponse.model_validate(data)
        return [YouTubeJobHandle(j, self) for j in page.jobs]

    def iter_all(
        self,
        *,
        status: JobStatus | None = None,
        page_size: int = 100,
    ) -> Iterator[YouTubeJobHandle]:
        offset = 0
        while True:
            params = {"limit": page_size, "offset": offset, "status": status}
            data = self._transport.request("GET", "/youtube-jobs", params=params)
            page = YouTubeJobListResponse.model_validate(data)
            for j in page.jobs:
                yield YouTubeJobHandle(j, self)
            if not page.pagination.has_more:
                return
            offset += page_size

    def _fetch_one(self, job_id: str) -> YouTubeJob:
        data = self._transport.request("GET", f"/youtube-jobs/{job_id}")
        return YouTubeJob.model_validate(data)


def _ext_from_url(url: str) -> str:
    head = url.split("?", 1)[0]
    suffix = Path(head).suffix
    return suffix if suffix else ""


__all__ = ["YouTubeJobHandle", "YouTubeJobsResource"]
