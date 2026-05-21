"""Stem-separation jobs (``/jobs``).

Public surface:

* :class:`JobsResource` — ``client.jobs.create / get / list / iter_all``.
* :class:`JobHandle` — what every method on :class:`JobsResource` returns.
  Adds the ergonomic helpers (``.wait()``, ``.iter_progress()``,
  ``.refresh()``, ``.download_all()``) on top of the immutable :class:`Job`
  data model.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from stemsplit_python._files import AudioInput, normalize_audio_input
from stemsplit_python.errors import JobExpiredError, JobFailedError
from stemsplit_python.models.jobs import (
    Job,
    JobListResponse,
    JobOutputFile,
    JobOutputs,
    JobOutputType,
    JobQuality,
    JobStatus,
    OutputFormat,
)

if TYPE_CHECKING:
    from stemsplit_python._transport import Transport
    from stemsplit_python.resources.uploads import UploadsResource


_STEMS_TO_OUTPUT_TYPE: dict[frozenset[str], JobOutputType] = {
    frozenset({"vocals"}): "VOCALS",
    frozenset({"instrumental"}): "INSTRUMENTAL",
    frozenset({"vocals", "instrumental"}): "BOTH",
    frozenset({"vocals", "drums", "bass", "other"}): "FOUR_STEMS",
    frozenset({"vocals", "drums", "bass", "other", "piano", "guitar"}): "SIX_STEMS",
}


def _stems_to_output_type(stems: Sequence[str] | None) -> JobOutputType | None:
    if stems is None:
        return None
    key = frozenset(s.lower() for s in stems)
    output_type = _STEMS_TO_OUTPUT_TYPE.get(key)
    if output_type is None:
        raise ValueError(
            f"Cannot infer outputType from stems={list(stems)}. The API supports "
            "VOCALS / INSTRUMENTAL / BOTH / FOUR_STEMS / SIX_STEMS — pass output_type "
            "directly for non-standard combinations."
        )
    return output_type


class JobHandle:
    """A live :class:`Job` with the convenience helpers attached.

    Returned from every :class:`JobsResource` method. Wraps an immutable
    :class:`Job` snapshot — calling :meth:`refresh` mutates the handle's
    internal pointer to a newer snapshot but never the snapshot itself.
    """

    def __init__(self, job: Job, resource: JobsResource) -> None:
        self._job = job
        self._resource = resource

    @property
    def job(self) -> Job:
        """The most recent immutable :class:`Job` snapshot."""

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
    def outputs(self) -> JobOutputs | None:
        """Per-stem download links (``None`` until the job completes)."""

        return self._job.outputs

    @property
    def audio_metadata(self) -> Any:
        return self._job.audio_metadata

    @property
    def is_terminal(self) -> bool:
        return self._job.status in {"COMPLETED", "FAILED", "EXPIRED"}

    def __repr__(self) -> str:
        return (
            f"JobHandle(id={self._job.id!r}, status={self._job.status!r}, "
            f"progress={self._job.progress})"
        )

    def refresh(self) -> Job:
        """Re-fetch the job from the API and return the new snapshot."""

        self._job = self._resource._fetch_one(self._job.id)
        return self._job

    def iter_progress(
        self,
        *,
        poll_interval: float = 5.0,
        timeout: float | None = 600.0,
    ) -> Iterator[Job]:
        """Yield successive :class:`Job` snapshots until the job ends.

        Polls ``GET /jobs/{id}`` every ``poll_interval`` seconds. Yields the
        current snapshot once at the start, then again after each poll.
        Stops when the job reaches ``COMPLETED`` / ``FAILED`` / ``EXPIRED``
        or when ``timeout`` elapses.
        """

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
        timeout: float = 600.0,
        poll_interval: float = 5.0,
    ) -> Job:
        """Block until the job reaches a terminal state and return the final :class:`Job`.

        Raises:
            TimeoutError: if the timeout expires before the job finishes.
            JobFailedError: if the job ends in ``FAILED``.
            JobExpiredError: if the job ends in ``EXPIRED``.
        """

        for snapshot in self.iter_progress(poll_interval=poll_interval, timeout=timeout):
            if snapshot.status == "COMPLETED":
                return snapshot
            if snapshot.status == "FAILED":
                raise JobFailedError(snapshot.id, snapshot.error_message)
            if snapshot.status == "EXPIRED":
                raise JobExpiredError(snapshot.id)
        raise TimeoutError(
            f"Timed out waiting for job {self._job.id} after {timeout}s "
            f"(last status: {self._job.status}, progress: {self._job.progress}%)."
        )

    def download_all(
        self,
        directory: str | Path,
        *,
        prefix: str | None = None,
    ) -> dict[str, Path]:
        """Download every available stem into ``directory``.

        Files are named ``<prefix><stem>.<ext>`` where the extension is
        inferred from the URL when present and falls back to ``.audio``.
        """

        outputs = self._job.outputs
        if outputs is None:
            raise RuntimeError(
                f"Job {self._job.id} has no outputs yet (status={self._job.status}). "
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


class JobsResource:
    """``client.jobs`` — create, get, list, iter_all."""

    def __init__(self, transport: Transport, uploads: UploadsResource) -> None:
        self._transport = transport
        self._uploads = uploads

    def create(
        self,
        *,
        audio: AudioInput | None = None,
        source_url: str | None = None,
        upload_key: str | None = None,
        stems: Sequence[str] | None = None,
        output_type: JobOutputType | None = None,
        quality: JobQuality | None = None,
        output_format: OutputFormat | None = None,
        file_name: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        callback_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> JobHandle:
        """Create a stem-separation job.

        Pass exactly one of ``audio`` (local file / bytes / file-like),
        ``source_url`` (publicly accessible audio URL) or ``upload_key``
        (the result of a prior ``client.uploads.create_ticket(...)``).

        ``stems`` is a friendly alias for ``output_type``: pass e.g.
        ``["vocals", "drums"]`` (any subset of vocals / drums / bass / other
        / piano / guitar / instrumental) and the SDK picks the right
        ``outputType`` enum value.
        """

        sources = [s is not None for s in (audio, source_url, upload_key)]
        if sum(sources) != 1:
            raise ValueError(
                "Pass exactly one of audio=, source_url= or upload_key= when creating a job."
            )

        body: dict[str, Any] = {}

        if stems is not None and output_type is not None:
            raise ValueError("Pass either stems= or output_type=, not both.")
        if stems is not None:
            output_type = _stems_to_output_type(stems)
        if output_type is not None:
            body["outputType"] = output_type
        if quality is not None:
            body["quality"] = quality
        if output_format is not None:
            body["outputFormat"] = output_format
        if metadata is not None:
            body["metadata"] = metadata
        if callback_url is not None:
            body["callbackUrl"] = callback_url

        if source_url is not None:
            body["sourceUrl"] = source_url
            if file_name is not None:
                body["fileName"] = file_name
        elif upload_key is not None:
            body["uploadKey"] = upload_key
            if file_name is not None:
                body["fileName"] = file_name
        else:
            assert audio is not None
            name, ctype, raw = normalize_audio_input(
                audio, file_name=file_name, content_type=content_type
            )
            ticket = self._uploads.create_ticket(filename=name, content_type=ctype)
            self._uploads.put_bytes(ticket, raw, content_type=ctype)
            body["uploadKey"] = ticket.upload_key
            body["fileName"] = name

        data = self._transport.request(
            "POST",
            "/jobs",
            json_body=body,
            idempotency_key=idempotency_key,
            retry_safe=True,
        )
        return JobHandle(Job.model_validate(data), self)

    def get(self, job_id: str) -> JobHandle:
        """Fetch a single job by id."""

        return JobHandle(self._fetch_one(job_id), self)

    def list(
        self,
        *,
        limit: int | None = 20,
        offset: int | None = 0,
        status: JobStatus | None = None,
    ) -> list[JobHandle]:
        """List jobs (one page).

        Filters: ``limit`` (≤100), ``offset``, ``status``. Use :meth:`iter_all`
        to walk every page.
        """

        params: dict[str, Any] = {"limit": limit, "offset": offset, "status": status}
        data = self._transport.request("GET", "/jobs", params=params)
        page = JobListResponse.model_validate(data)
        return [JobHandle(j, self) for j in page.jobs]

    def iter_all(
        self,
        *,
        status: JobStatus | None = None,
        page_size: int = 100,
    ) -> Iterator[JobHandle]:
        """Yield every matching job by walking pagination transparently."""

        offset = 0
        while True:
            params = {"limit": page_size, "offset": offset, "status": status}
            data = self._transport.request("GET", "/jobs", params=params)
            page = JobListResponse.model_validate(data)
            for j in page.jobs:
                yield JobHandle(j, self)
            if not page.pagination.has_more:
                return
            offset += page_size

    def _fetch_one(self, job_id: str) -> Job:
        data = self._transport.request("GET", f"/jobs/{job_id}")
        return Job.model_validate(data)


def _ext_from_url(url: str) -> str:
    """Best-effort file extension from a presigned URL."""

    head = url.split("?", 1)[0]
    suffix = Path(head).suffix
    return suffix if suffix else ""


__all__ = ["JobHandle", "JobOutputFile", "JobsResource"]
