"""Exception hierarchy for the StemSplit SDK.

The shape mirrors `openai-python` and `stripe-python` so that anyone with
muscle memory from those SDKs can transfer it here directly.

Hierarchy::

    StemSplitError                          (base)
    ├── APIError                            (transport / parse failures)
    │   └── APITimeoutError                 (request exceeded the client timeout)
    └── APIStatusError                      (HTTP non-2xx)
        ├── BadRequestError                 (400)
        ├── AuthenticationError             (401)
        ├── PermissionDeniedError           (403)
        ├── InsufficientCreditsError        (402)
        ├── NotFoundError                   (404)
        ├── ConflictError                   (409)
        ├── UnprocessableEntityError        (422)
        ├── RateLimitError                  (429)
        └── InternalServerError             (5xx)

    JobFailedError                          (logical: surfaced by .wait())
    JobExpiredError                         (logical: surfaced by .wait())
    SignatureVerificationError              (webhook signature mismatch)

Each ``APIStatusError`` exposes ``status_code``, ``code`` (the API's
``error.code`` string when present), ``message``, ``request_id`` and the
parsed ``response_json`` body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class StemSplitError(Exception):
    """Base class for every error raised by this SDK."""


class APIError(StemSplitError):
    """A transport-level failure: DNS, connection reset, JSON parse error, …

    Anything where the HTTP layer itself failed before we got a response we
    could classify by status code.
    """

    def __init__(self, message: str, *, request: httpx.Request | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.request = request


class APITimeoutError(APIError):
    """The request did not complete within the configured timeout."""


class APIStatusError(StemSplitError):
    """The server returned a non-2xx HTTP status code."""

    status_code: int = 0

    def __init__(
        self,
        message: str,
        *,
        response: httpx.Response,
        body: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.response = response
        self.status_code = response.status_code
        self.response_json = body if isinstance(body, dict) else None
        err_block = self.response_json.get("error") if self.response_json else None
        if isinstance(err_block, dict):
            self.code: str | None = err_block.get("code")
            self.error_message: str | None = err_block.get("message")
        else:
            self.code = None
            self.error_message = None
        self.request_id: str | None = response.headers.get("x-request-id")

    def __str__(self) -> str:
        parts = [f"{self.status_code}"]
        if self.code:
            parts.append(self.code)
        parts.append(self.error_message or self.message)
        if self.request_id:
            parts.append(f"(request_id={self.request_id})")
        return " ".join(parts)


class BadRequestError(APIStatusError):
    """HTTP 400. ``code`` is one of FILE_TOO_LARGE, AUDIO_TOO_LONG,
    AUDIO_TOO_SHORT, UNSUPPORTED_FORMAT (per the docs error-code table)."""

    status_code = 400


class AuthenticationError(APIStatusError):
    """HTTP 401. ``code`` is MISSING_API_KEY or INVALID_API_KEY."""

    status_code = 401


class InsufficientCreditsError(APIStatusError):
    """HTTP 402. The account does not have enough credits for this job.

    The response body includes ``requiredSeconds`` and ``purchaseUrl`` which
    are exposed as :attr:`required_seconds` and :attr:`purchase_url`.
    """

    status_code = 402

    def __init__(
        self,
        message: str,
        *,
        response: httpx.Response,
        body: Any | None = None,
    ) -> None:
        super().__init__(message, response=response, body=body)
        err = (body or {}).get("error") if isinstance(body, dict) else None
        self.required_seconds: int | None = (
            err.get("requiredSeconds") if isinstance(err, dict) else None
        )
        self.purchase_url: str | None = err.get("purchaseUrl") if isinstance(err, dict) else None


class PermissionDeniedError(APIStatusError):
    """HTTP 403. ``code`` is API_KEY_REVOKED."""

    status_code = 403


class NotFoundError(APIStatusError):
    """HTTP 404. ``code`` is JOB_NOT_FOUND for the jobs resource."""

    status_code = 404


class ConflictError(APIStatusError):
    """HTTP 409."""

    status_code = 409


class UnprocessableEntityError(APIStatusError):
    """HTTP 422."""

    status_code = 422


class RateLimitError(APIStatusError):
    """HTTP 429. Exposes :attr:`retry_after`, plus the ``X-RateLimit-*`` headers."""

    status_code = 429

    def __init__(
        self,
        message: str,
        *,
        response: httpx.Response,
        body: Any | None = None,
    ) -> None:
        super().__init__(message, response=response, body=body)
        self.retry_after: int | None = _int_header(response, "retry-after")
        self.limit: int | None = _int_header(response, "x-ratelimit-limit")
        self.remaining: int | None = _int_header(response, "x-ratelimit-remaining")
        self.reset_at: int | None = _int_header(response, "x-ratelimit-reset")


class InternalServerError(APIStatusError):
    """HTTP 5xx."""

    status_code = 500


class JobFailedError(StemSplitError):
    """Raised by :meth:`Job.wait` when the job ends in ``FAILED``."""

    def __init__(self, job_id: str, error_message: str | None) -> None:
        msg = f"Job {job_id} failed: {error_message or 'Unknown error'}"
        super().__init__(msg)
        self.job_id = job_id
        self.error_message = error_message


class JobExpiredError(StemSplitError):
    """Raised by :meth:`Job.wait` when the job moved to ``EXPIRED``."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job {job_id} has expired")
        self.job_id = job_id


class SignatureVerificationError(StemSplitError):
    """Raised by :func:`stemsplit_python.webhooks.verify_and_parse` when the
    HMAC signature on a webhook delivery does not match.
    """


def _int_header(response: httpx.Response, name: str) -> int | None:
    raw = response.headers.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


_STATUS_TO_EXCEPTION: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    402: InsufficientCreditsError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def exception_for_response(response: httpx.Response, body: Any | None) -> APIStatusError:
    """Pick the right :class:`APIStatusError` subclass for an HTTP response."""

    status = response.status_code
    cls = _STATUS_TO_EXCEPTION.get(status)
    if cls is None:
        if 500 <= status < 600:
            cls = InternalServerError
        else:
            cls = APIStatusError
    err = (body or {}).get("error") if isinstance(body, dict) else None
    message: str = f"HTTP {status}"
    if isinstance(err, dict):
        candidate = err.get("message")
        if isinstance(candidate, str) and candidate:
            message = candidate
    return cls(message, response=response, body=body)


__all__ = [
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "InsufficientCreditsError",
    "InternalServerError",
    "JobExpiredError",
    "JobFailedError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "SignatureVerificationError",
    "StemSplitError",
    "UnprocessableEntityError",
    "exception_for_response",
]
