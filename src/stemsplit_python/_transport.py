"""Thin wrapper around ``httpx.Client``.

Responsibilities:

* Bearer auth.
* User-Agent string.
* Retries on idempotent verbs and ``429``/``5xx`` (honors ``Retry-After``).
* Rate-limit header parsing exposed via :attr:`Transport.last_rate_limit`.
* Mapping non-2xx responses to typed exceptions in :mod:`stemsplit_python.errors`.
"""

from __future__ import annotations

import platform
import sys
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from stemsplit_python._version import __version__
from stemsplit_python.errors import (
    APIError,
    APIStatusError,
    APITimeoutError,
    exception_for_response,
)

DEFAULT_BASE_URL = "https://stemsplit.io/api/v1"
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=5.0)
UPLOAD_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=600.0, pool=5.0)
DEFAULT_MAX_RETRIES = 3

HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


@dataclass(frozen=True)
class RateLimit:
    """Parsed ``X-RateLimit-*`` headers from the most recent response."""

    limit: int | None
    remaining: int | None
    reset_at: int | None
    retry_after: int | None


def _user_agent() -> str:
    py = sys.version_info
    return (
        f"stemsplit-python/{__version__} "
        f"python/{py.major}.{py.minor}.{py.micro} "
        f"httpx/{httpx.__version__} "
        f"({platform.system().lower()})"
    )


class Transport:
    """Sync HTTP transport used by every SDK resource."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: httpx.Timeout | float | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max(0, max_retries)
        self._owns_client = http_client is None
        if http_client is None:
            self._client = httpx.Client(
                timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
                headers={"User-Agent": _user_agent()},
            )
        else:
            self._client = http_client
        self._last_rate_limit: RateLimit | None = None

    @property
    def last_rate_limit(self) -> RateLimit | None:
        """The ``X-RateLimit-*`` headers parsed from the most recent response.

        ``None`` until the first request completes.
        """

        return self._last_rate_limit

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Transport:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def request(
        self,
        method: HttpMethod,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        retry_safe: bool | None = None,
    ) -> Any:
        """Perform an authenticated request and return parsed JSON.

        ``path`` may be an absolute URL (used internally for the presigned
        upload PUT) or a path beginning with ``/`` joined to ``base_url``.

        ``retry_safe`` defaults to ``True`` for ``GET`` and to ``False``
        otherwise. Override it for endpoints we know are safe to replay
        (e.g. ``POST /upload``, polling).
        """

        url = path if path.startswith("http") else f"{self.base_url}{path}"
        request_headers: dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)
        if idempotency_key:
            request_headers["Idempotency-Key"] = idempotency_key

        params_clean = {k: v for k, v in params.items() if v is not None} if params else None

        retry_safe_resolved = retry_safe if retry_safe is not None else method == "GET"
        attempts = self.max_retries + 1 if retry_safe_resolved else 1

        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params_clean,
                    json=json_body,
                    headers=request_headers,
                )
            except httpx.TimeoutException as exc:
                last_exc = APITimeoutError(
                    f"Timed out talking to {url}: {exc}",
                    request=getattr(exc, "request", None),
                )
                if attempt < attempts - 1:
                    self._sleep_backoff(attempt)
                    continue
                raise last_exc from exc
            except httpx.HTTPError as exc:
                last_exc = APIError(
                    f"Connection error talking to {url}: {exc}",
                    request=getattr(exc, "request", None),
                )
                if attempt < attempts - 1:
                    self._sleep_backoff(attempt)
                    continue
                raise last_exc from exc

            self._capture_rate_limit(response)

            if 200 <= response.status_code < 300:
                return self._parse_json(response)

            if (
                response.status_code in {429} or 500 <= response.status_code < 600
            ) and attempt < attempts - 1:
                retry_after = _retry_after_seconds(response)
                self._sleep_backoff(attempt, retry_after)
                continue

            body = self._parse_json(response, allow_empty=True)
            raise exception_for_response(response, body)

        if last_exc:
            raise last_exc
        raise APIError("Exhausted retries with no exception captured")

    def stream_to_file(self, url: str, dest: Any) -> int:
        """Stream ``url`` to ``dest`` (a path or file-like object).

        Used for download helpers — does not send the API auth token (the
        URL is already a presigned link to object storage).
        """

        from pathlib import Path

        with self._client.stream("GET", url) as response:
            if response.status_code != 200:
                raise APIError(f"Failed to download {url}: HTTP {response.status_code}")
            written = 0
            if isinstance(dest, (str, Path)):
                Path(dest).parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as fp:
                    for chunk in response.iter_bytes():
                        fp.write(chunk)
                        written += len(chunk)
            else:
                for chunk in response.iter_bytes():
                    dest.write(chunk)
                    written += len(chunk)
            return written

    def put_to_presigned_url(
        self,
        url: str,
        body: Any,
        content_type: str,
        *,
        content_length: int | None = None,
    ) -> None:
        """PUT raw bytes to a presigned upload URL.

        We deliberately do **not** include the SDK's bearer token here —
        S3/R2 will reject signed requests that also carry ``Authorization``.
        """

        headers = {"Content-Type": content_type}
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        try:
            response = self._client.put(url, content=body, headers=headers, timeout=UPLOAD_TIMEOUT)
        except httpx.TimeoutException as exc:
            raise APITimeoutError(f"Timed out uploading to {url}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise APIError(f"Connection error uploading to {url}: {exc}") from exc
        if response.status_code >= 300:
            raise APIError(
                f"Presigned upload failed: HTTP {response.status_code} {response.text[:200]}"
            )

    def _sleep_backoff(self, attempt: int, retry_after: float | None = None) -> None:
        if retry_after is not None:
            time.sleep(min(retry_after, 60))
            return
        # Exponential backoff: 0.5s, 1s, 2s, 4s, capped at 8s.
        delay = min(0.5 * (2**attempt), 8.0)
        time.sleep(delay)

    def _capture_rate_limit(self, response: httpx.Response) -> None:
        def _i(name: str) -> int | None:
            raw = response.headers.get(name)
            if raw is None:
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        if "x-ratelimit-limit" not in response.headers:
            return
        self._last_rate_limit = RateLimit(
            limit=_i("x-ratelimit-limit"),
            remaining=_i("x-ratelimit-remaining"),
            reset_at=_i("x-ratelimit-reset"),
            retry_after=_i("retry-after"),
        )

    @staticmethod
    def _parse_json(response: httpx.Response, *, allow_empty: bool = False) -> Any:
        if not response.content:
            if allow_empty:
                return None
            raise APIError("Server returned an empty body where JSON was expected")
        try:
            return response.json()
        except ValueError as exc:
            if allow_empty:
                return None
            raise APIError(f"Failed to parse JSON response: {exc}") from exc


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "APIStatusError",
    "RateLimit",
    "Transport",
]
