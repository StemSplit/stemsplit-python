"""Webhook signature verification + parsing.

Use the top-level :func:`verify_and_parse` in your HTTP handler — it does
the HMAC compare in constant time and returns a typed
:class:`stemsplit_python.WebhookEvent` on success::

    from stemsplit_python import webhooks, SignatureVerificationError

    @app.post("/stemsplit-webhook")
    def handler(request):
        try:
            event = webhooks.verify_and_parse(
                payload=request.body,
                signature=request.headers["X-Webhook-Signature"],
                secret=os.environ["STEMSPLIT_WEBHOOK_SECRET"],
            )
        except SignatureVerificationError:
            return Response(status_code=401)
        if event.event == "job.completed":
            print(event.data.job_id, event.data.outputs)
        return Response(status_code=200)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from stemsplit_python.errors import SignatureVerificationError
from stemsplit_python.models.webhooks import WebhookEvent

__all__ = [
    "compute_signature",
    "verify_and_parse",
    "verify_signature",
]


def compute_signature(payload: bytes, secret: str) -> str:
    """Return the canonical signature (``sha256=<hex>``) for ``payload``.

    Useful for logging or driving tests; production code should use
    :func:`verify_signature` so the comparison is constant-time.
    """

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Return ``True`` iff ``signature`` matches the HMAC of ``payload``.

    Accepts both ``sha256=<hex>`` (the wire format) and bare ``<hex>``.
    """

    if not signature:
        return False
    expected = compute_signature(payload, secret)
    candidate = signature.strip()
    if not candidate.startswith("sha256="):
        candidate = f"sha256={candidate}"
    return hmac.compare_digest(expected, candidate)


def verify_and_parse(
    *,
    payload: bytes | str,
    signature: str,
    secret: str,
) -> WebhookEvent:
    """Verify the signature and return a typed :class:`WebhookEvent`.

    Raises:
        SignatureVerificationError: if the signature doesn't match. Always
            raise this and return 401 — never trust the body otherwise.
        ValueError: if the body isn't valid JSON. (Indicates a bug in the
            sender, not a security issue.)
    """

    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    if not verify_signature(raw, signature, secret):
        raise SignatureVerificationError(
            "Webhook signature does not match. Check that you are passing the raw "
            "request body (not the parsed JSON) and the correct signing secret."
        )
    parsed: Any = json.loads(raw)
    return WebhookEvent.model_validate(parsed)
