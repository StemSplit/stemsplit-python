# Changelog

All notable changes to `stemsplit-python` are documented here. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-05-21 — Initial release: sync SDK for the StemSplit API

First public release. Synchronous Python client for the official
[StemSplit](https://stemsplit.io) hosted stem-separation API.

### Added

- **`StemSplit` sync client** (`AsyncStemSplit` placeholder pointing at
  v0.2). Bearer-auth, env-var key default (`STEMSPLIT_API_KEY`),
  configurable base URL, soft `sk_live_` prefix validation.
- **Resources for every public endpoint:**
  - `client.jobs` — create (file / bytes / file-like / `source_url` /
    `upload_key`), get, list, `iter_all`, with the killer ergonomic
    layer: `JobHandle.wait()`, `.iter_progress()`, `.refresh()`,
    `.download_all()`.
  - `client.youtube_jobs` — create from YouTube URL, get, list,
    `iter_all`, same `wait()` / `download_all()` ergonomics. Surfaces
    video metadata (`video_title`, `video_duration`, `channel_name`,
    `youtube_url`) and the YouTube-specific `full_audio` output.
  - `client.uploads` — presigned-URL helpers (`create_ticket`,
    `upload_bytes`) for the rare case where you want to manage uploads
    yourself.
  - `client.account` — `balance()` / `get()` returning typed `Balance`.
  - `client.webhooks` — `create`, `list`, `delete`. Capture `secret`
    from `create()`; the API never returns it again.
- **Webhook signature verification** (`stemsplit_python.webhooks`):
  `verify_signature` for raw-bytes verification and `verify_and_parse`
  that returns a typed `WebhookEvent`. Constant-time HMAC-SHA256
  comparison, accepts both `sha256=<hex>` and bare hex.
- **Stripe-style error hierarchy** mapping API responses 1:1 to typed
  exceptions: `BadRequestError` (400), `AuthenticationError` (401),
  `InsufficientCreditsError` (402, with `.required_seconds` /
  `.purchase_url`), `PermissionDeniedError` (403), `NotFoundError`
  (404), `ConflictError` (409), `UnprocessableEntityError` (422),
  `RateLimitError` (429, with `.retry_after` / `.limit` /
  `.remaining` / `.reset_at`), `InternalServerError` (5xx). Plus
  logical errors `JobFailedError`, `JobExpiredError`,
  `SignatureVerificationError`.
- **Retries with backoff** on `429` and `5xx` for safe-to-replay verbs
  (default `max_retries=3`). Honors `Retry-After` when present.
- **Rate-limit awareness:** parses `X-RateLimit-*` headers on every
  response, exposed as `client.last_rate_limit`.
- **Idempotency-Key passthrough** on `jobs.create`, `youtube_jobs.create`,
  `webhooks.create`. Forwarded as a header today; lights up
  automatically when the API ships server-side support.
- **Audio metadata (BPM / key)** on completed jobs: `Job.audio_metadata`
  and `YouTubeJob.audio_metadata` typed as `AudioMetadata { bpm, key }`.
  Both fields are optional and degrade gracefully if the analysis
  doesn't run.
- **Pydantic v2 models** with `frozen=True`, `extra="allow"` (forward-
  compatible against new server fields), snake_case Python attributes
  aliased to the camelCase wire fields, and `Literal[...]` unions for
  every status / quality / format value (no `enum.Enum`).
- **Typing:** `py.typed` marker shipped, `mypy --strict` clean.
- **Three runtime dependencies only:** `httpx`, `pydantic`,
  `typing-extensions` (Python 3.10 backport only). No PyTorch, no
  numpy, no native code.
- **Snapshot of the live OpenAPI 3.1 spec** at
  `openapi/openapi.json` so future versions can diff API drift.

### Tested

- 62 tests, ~92 % line coverage, all `respx`-backed mocks. Full status-
  code → exception matrix, retry behavior, end-to-end
  `jobs.create(audio=Path)` chain, `wait()` happy / failed / timeout
  paths, webhook signature round-trip + tamper detection, and YouTube
  job lifecycle.

### Deferred

- **`AsyncStemSplit`** — lands in v0.2. Constructing it today raises
  `NotImplementedError` with a pointer at the tracking issue.
- **`job.cancel()`** — the API does not yet expose `DELETE /jobs/{id}`;
  honest omission rather than a no-op stub. Will land alongside the
  endpoint.
- **CLI** — a separate `stemsplit-cli` add-on is planned for v0.2 so
  the SDK stays dependency-light.

[0.1.0]: https://github.com/StemSplit/stemsplit-python/releases/tag/v0.1.0
