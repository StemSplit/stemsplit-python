"""Webhook signature verification + parsing."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from stemsplit_python import SignatureVerificationError, webhooks

SECRET = "whsec_super_secret"


def _sign(payload: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_round_trip() -> None:
    payload = b'{"event":"job.completed"}'
    assert webhooks.verify_signature(payload, _sign(payload), SECRET)


def test_verify_accepts_bare_hex() -> None:
    payload = b"hello"
    sig = _sign(payload).removeprefix("sha256=")
    assert webhooks.verify_signature(payload, sig, SECRET)


def test_verify_rejects_tampered_body() -> None:
    payload = b"original"
    sig = _sign(payload)
    assert not webhooks.verify_signature(b"tampered", sig, SECRET)


def test_verify_rejects_wrong_secret() -> None:
    payload = b"original"
    sig = _sign(payload, secret="other")
    assert not webhooks.verify_signature(payload, sig, SECRET)


def test_verify_rejects_empty_signature() -> None:
    assert not webhooks.verify_signature(b"original", "", SECRET)


def test_verify_and_parse_returns_typed_event() -> None:
    body = {
        "event": "job.completed",
        "timestamp": "2026-05-21T12:30:00Z",
        "data": {
            "jobId": "job_abc",
            "status": "COMPLETED",
            "input": {"fileName": "song.mp3", "durationSeconds": 180},
            "options": {"outputType": "BOTH", "quality": "BEST", "outputFormat": "MP3"},
            "outputs": {
                "vocals": {
                    "url": "https://x/vocals.mp3",
                    "expiresAt": "2026-05-21T13:30:00Z",
                }
            },
            "creditsCharged": 180,
            "createdAt": "2026-05-21T12:00:00Z",
            "completedAt": "2026-05-21T12:02:30Z",
        },
    }
    raw = json.dumps(body).encode()
    event = webhooks.verify_and_parse(payload=raw, signature=_sign(raw), secret=SECRET)
    assert event.event == "job.completed"
    assert event.data.job_id == "job_abc"
    assert event.data.outputs is not None
    assert event.data.outputs.vocals is not None


def test_verify_and_parse_rejects_bad_signature() -> None:
    raw = b'{"event":"job.completed"}'
    with pytest.raises(SignatureVerificationError):
        webhooks.verify_and_parse(payload=raw, signature="sha256=deadbeef", secret=SECRET)
