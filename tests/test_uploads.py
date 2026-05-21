"""Direct uploads resource tests."""

from __future__ import annotations

import httpx
import respx

from stemsplit_python import StemSplit


@respx.mock
def test_create_ticket_returns_upload_ticket() -> None:
    respx.post("https://stemsplit.io/api/v1/upload").mock(
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
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    ticket = client.uploads.create_ticket(filename="song.mp3")
    assert ticket.upload_key == "uploads/test/song.mp3"
    assert ticket.content_type == "audio/mpeg"


@respx.mock
def test_upload_bytes_does_two_step_flow() -> None:
    presign = respx.post("https://stemsplit.io/api/v1/upload").mock(
        return_value=httpx.Response(
            200,
            json={
                "uploadUrl": "https://storage.example.com/presign?sig=x",
                "uploadKey": "uploads/test/song.mp3",
                "expiresAt": "2026-05-21T12:15:00Z",
                "maxFileSizeMb": 50,
                "contentType": "audio/mpeg",
            },
        )
    )
    put = respx.put("https://storage.example.com/presign").respond(200)
    client = StemSplit(api_key="sk_live_test", max_retries=0)
    ticket = client.uploads.upload_bytes(filename="song.mp3", data=b"\xff" * 16)
    assert ticket.upload_key == "uploads/test/song.mp3"
    assert presign.called
    assert put.called
