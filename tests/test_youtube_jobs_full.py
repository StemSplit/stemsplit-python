"""Extra coverage for the youtube_jobs handle and pagination."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from stemsplit_python import JobFailedError, StemSplit


def _yt_job(job_id: str = "yt_1", *, status: str = "COMPLETED") -> dict:
    return {
        "id": job_id,
        "status": status,
        "progress": 100 if status == "COMPLETED" else 0,
        "createdAt": "2026-05-21T12:00:00Z",
        "videoTitle": "Some Video",
        "outputs": {
            "fullAudio": {
                "url": "https://storage.example.com/full.mp3?sig=x",
                "expiresAt": "2026-05-21T13:00:00Z",
            },
            "vocals": {
                "url": "https://storage.example.com/vocals.mp3?sig=x",
                "expiresAt": "2026-05-21T13:00:00Z",
            },
            "instrumental": {
                "url": "https://storage.example.com/instrumental.mp3?sig=x",
                "expiresAt": "2026-05-21T13:00:00Z",
            },
        }
        if status == "COMPLETED"
        else None,
    }


@respx.mock
def test_youtube_list_and_iter_all() -> None:
    page1 = {
        "jobs": [_yt_job("yt_1"), _yt_job("yt_2")],
        "pagination": {"total": 3, "limit": 2, "offset": 0, "hasMore": True},
    }
    page2 = {
        "jobs": [_yt_job("yt_3")],
        "pagination": {"total": 3, "limit": 2, "offset": 2, "hasMore": False},
    }
    respx.get("https://stemsplit.io/api/v1/youtube-jobs").mock(
        side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    listed = client.youtube_jobs.list(limit=2)
    assert [h.id for h in listed] == ["yt_1", "yt_2"]

    respx.get("https://stemsplit.io/api/v1/youtube-jobs").mock(
        side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    )
    ids = [h.id for h in client.youtube_jobs.iter_all(page_size=2)]
    assert ids == ["yt_1", "yt_2", "yt_3"]


@respx.mock
def test_youtube_wait_completes() -> None:
    pending = _yt_job("yt_1", status="PROCESSING")
    completed = _yt_job("yt_1", status="COMPLETED")
    respx.get("https://stemsplit.io/api/v1/youtube-jobs/yt_1").mock(
        side_effect=[
            httpx.Response(200, json=pending),
            httpx.Response(200, json=completed),
        ]
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.youtube_jobs.get("yt_1")
    snapshot = handle.wait(timeout=5.0, poll_interval=0.01)
    assert snapshot.status == "COMPLETED"


@respx.mock
def test_youtube_wait_raises_on_failed() -> None:
    failing = {
        "id": "yt_1",
        "status": "FAILED",
        "progress": 0,
        "createdAt": "2026-05-21T12:00:00Z",
        "errorMessage": "Video private",
    }
    respx.get("https://stemsplit.io/api/v1/youtube-jobs/yt_1").mock(
        return_value=httpx.Response(200, json=failing)
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.youtube_jobs.get("yt_1")
    with pytest.raises(JobFailedError):
        handle.wait(timeout=5.0, poll_interval=0.01)


@respx.mock
def test_youtube_download_all_writes_files(tmp_path: Path) -> None:
    respx.get("https://stemsplit.io/api/v1/youtube-jobs/yt_1").mock(
        return_value=httpx.Response(200, json=_yt_job("yt_1"))
    )
    for stem in ("full", "vocals", "instrumental"):
        respx.get(f"https://storage.example.com/{stem}.mp3", params={"sig": "x"}).respond(
            200, content=f"{stem}-bytes".encode()
        )

    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.youtube_jobs.get("yt_1")
    paths = handle.download_all(tmp_path)
    assert paths["full_audio"].read_bytes() == b"full-bytes"
    assert paths["vocals"].read_bytes() == b"vocals-bytes"


def test_youtube_create_requires_url() -> None:
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    with pytest.raises(ValueError, match="Pass url"):
        client.youtube_jobs.create()
