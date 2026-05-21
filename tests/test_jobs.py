"""End-to-end happy paths for the jobs resource."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from stemsplit_python import JobFailedError, StemSplit


def _completed_job(
    job_id: str = "job_abc",
    *,
    status: str = "COMPLETED",
    progress: int = 100,
    with_metadata: bool = True,
) -> dict:
    body: dict = {
        "id": job_id,
        "status": status,
        "progress": progress,
        "createdAt": "2026-05-21T12:00:00Z",
        "completedAt": "2026-05-21T12:02:30Z",
        "input": {"fileName": "song.mp3", "durationSeconds": 180},
        "options": {"outputType": "BOTH", "quality": "BEST", "outputFormat": "MP3"},
        "outputs": {
            "vocals": {
                "url": "https://storage.example.com/vocals.mp3?sig=x",
                "expiresAt": "2026-05-21T13:00:00Z",
            },
            "instrumental": {
                "url": "https://storage.example.com/instrumental.mp3?sig=x",
                "expiresAt": "2026-05-21T13:00:00Z",
            },
        },
        "creditsCharged": 180,
    }
    if with_metadata:
        body["audioMetadata"] = {"bpm": 120.0, "key": "Gm"}
    return body


@respx.mock
def test_create_from_source_url() -> None:
    respx.post("https://stemsplit.io/api/v1/jobs").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "job_abc",
                "status": "PENDING",
                "progress": 0,
                "createdAt": "2026-05-21T12:00:00Z",
                "creditsRequired": 180,
                "options": {"outputType": "BOTH", "quality": "BEST", "outputFormat": "MP3"},
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.jobs.create(
        source_url="https://example.com/song.mp3",
        output_type="BOTH",
        quality="BEST",
        output_format="MP3",
    )
    assert handle.id == "job_abc"
    assert handle.status == "PENDING"
    assert handle.job.credits_required == 180


@respx.mock
def test_create_from_local_file_runs_two_step_upload(tmp_path: Path) -> None:
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"\x00\x01" * 32)

    upload_route = respx.post("https://stemsplit.io/api/v1/upload").mock(
        return_value=httpx.Response(
            200,
            json={
                "uploadUrl": "https://storage.example.com/presign?sig=x",
                "uploadKey": "uploads/test/song.mp3",
                "expiresAt": "2026-05-21T12:15:00Z",
                "maxFileSizeBytes": 50 * 1024 * 1024,
                "maxFileSizeMb": 50,
                "contentType": "audio/mpeg",
            },
        )
    )
    put_route = respx.put("https://storage.example.com/presign").respond(200)
    create_route = respx.post("https://stemsplit.io/api/v1/jobs").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "job_abc",
                "status": "PENDING",
                "progress": 0,
                "createdAt": "2026-05-21T12:00:00Z",
            },
        )
    )

    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.jobs.create(audio=audio_path, stems=["vocals", "instrumental"])

    assert upload_route.called
    assert put_route.called
    assert create_route.called
    body = create_route.calls.last.request.read().decode()
    assert "uploadKey" in body
    assert "BOTH" in body
    assert handle.id == "job_abc"


@respx.mock
def test_get_returns_handle_with_audio_metadata() -> None:
    respx.get("https://stemsplit.io/api/v1/jobs/job_abc").mock(
        return_value=httpx.Response(200, json=_completed_job())
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.jobs.get("job_abc")
    assert handle.status == "COMPLETED"
    assert handle.audio_metadata is not None
    assert handle.audio_metadata.bpm == 120.0
    assert handle.audio_metadata.key == "Gm"
    assert handle.outputs is not None
    assert handle.outputs.vocals is not None


@respx.mock
def test_wait_polls_until_completed() -> None:
    pending = {
        "id": "job_abc",
        "status": "PROCESSING",
        "progress": 40,
        "createdAt": "2026-05-21T12:00:00Z",
    }
    respx.get("https://stemsplit.io/api/v1/jobs/job_abc").mock(
        side_effect=[
            httpx.Response(200, json=pending),
            httpx.Response(200, json=_completed_job()),
        ]
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.jobs.get("job_abc")
    snapshot = handle.wait(timeout=5.0, poll_interval=0.01)
    assert snapshot.status == "COMPLETED"


@respx.mock
def test_wait_raises_on_failed() -> None:
    failing = {
        "id": "job_abc",
        "status": "FAILED",
        "progress": 50,
        "createdAt": "2026-05-21T12:00:00Z",
        "errorMessage": "Audio too short",
    }
    respx.get("https://stemsplit.io/api/v1/jobs/job_abc").mock(
        return_value=httpx.Response(200, json=failing)
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.jobs.get("job_abc")
    with pytest.raises(JobFailedError) as exc:
        handle.wait(timeout=5.0, poll_interval=0.01)
    assert exc.value.error_message == "Audio too short"


@respx.mock
def test_list_jobs_returns_handles() -> None:
    respx.get("https://stemsplit.io/api/v1/jobs").mock(
        return_value=httpx.Response(
            200,
            json={
                "jobs": [_completed_job("job_1"), _completed_job("job_2")],
                "pagination": {"total": 2, "limit": 20, "offset": 0, "hasMore": False},
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handles = client.jobs.list(limit=20, status="COMPLETED")
    assert [h.id for h in handles] == ["job_1", "job_2"]


@respx.mock
def test_iter_all_walks_pagination() -> None:
    page1 = {
        "jobs": [_completed_job("job_1"), _completed_job("job_2")],
        "pagination": {"total": 3, "limit": 2, "offset": 0, "hasMore": True},
    }
    page2 = {
        "jobs": [_completed_job("job_3")],
        "pagination": {"total": 3, "limit": 2, "offset": 2, "hasMore": False},
    }
    respx.get("https://stemsplit.io/api/v1/jobs").mock(
        side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    ids = [h.id for h in client.jobs.iter_all(page_size=2)]
    assert ids == ["job_1", "job_2", "job_3"]


@respx.mock
def test_download_all_writes_files(tmp_path: Path) -> None:
    respx.get("https://stemsplit.io/api/v1/jobs/job_abc").mock(
        return_value=httpx.Response(200, json=_completed_job())
    )
    respx.get("https://storage.example.com/vocals.mp3", params={"sig": "x"}).respond(
        200, content=b"vocal-bytes"
    )
    respx.get("https://storage.example.com/instrumental.mp3", params={"sig": "x"}).respond(
        200, content=b"instrumental-bytes"
    )

    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.jobs.get("job_abc")
    paths = handle.download_all(tmp_path)
    assert paths["vocals"].read_bytes() == b"vocal-bytes"
    assert paths["instrumental"].read_bytes() == b"instrumental-bytes"


def test_create_validates_exactly_one_input_source() -> None:
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    with pytest.raises(ValueError, match="exactly one"):
        client.jobs.create()
    with pytest.raises(ValueError, match="exactly one"):
        client.jobs.create(source_url="x", upload_key="y")
