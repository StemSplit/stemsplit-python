"""YouTube jobs resource tests (parallel to test_jobs.py)."""

from __future__ import annotations

import httpx
import respx

from stemsplit_python import StemSplit


@respx.mock
def test_create_youtube_job() -> None:
    route = respx.post("https://stemsplit.io/api/v1/youtube-jobs").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "ytjob_xyz",
                "status": "PENDING",
                "progress": 0,
                "createdAt": "2026-05-21T12:00:00Z",
                "videoId": "dQw4w9WgXcQ",
                "videoTitle": "Never Gonna Give You Up",
                "videoDuration": 213,
                "channelName": "Rick Astley",
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.youtube_jobs.create(url="https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert handle.id == "ytjob_xyz"
    assert handle.video_title == "Never Gonna Give You Up"
    body = route.calls.last.request.read().decode()
    assert "youtubeUrl" in body


@respx.mock
def test_get_youtube_job_with_full_audio_output() -> None:
    respx.get("https://stemsplit.io/api/v1/youtube-jobs/ytjob_xyz").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "ytjob_xyz",
                "status": "COMPLETED",
                "progress": 100,
                "createdAt": "2026-05-21T12:00:00Z",
                "videoTitle": "Never Gonna Give You Up",
                "audioMetadata": {"bpm": 113.0, "key": "Am"},
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
                },
            },
        )
    )
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    handle = client.youtube_jobs.get("ytjob_xyz")
    assert handle.status == "COMPLETED"
    assert handle.outputs is not None
    assert handle.outputs.full_audio is not None
    assert handle.outputs.vocals is not None
