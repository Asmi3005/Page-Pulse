# Page Pulse

URL audit API built with FastAPI.

## Features

- Audit any HTTP/HTTPS webpage through a single REST API
- Configurable cache TTL via environment variables
- Per-client rate limiting (by IP) on `POST /audit`
- Outbound concurrency limiting with `asyncio.Semaphore`
- Structured logging with a UUID `request_id` per request
- Async `httpx` fetches with a 10-second timeout
- Consistent JSON success/error responses

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `CACHE_TTL_SECONDS` | `300` | How long audit results stay cached |
| `CACHE_MAX_SIZE` | `256` | Max cached URLs |
| `RATE_LIMIT_REQUESTS` | `30` | Max `/audit` requests per client per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window in seconds |
| `MAX_OUTBOUND_REQUESTS` | `3` | Max simultaneous outbound HTTP fetches |
| `REQUEST_TIMEOUT_SECONDS` | `10` | Outbound fetch timeout |

Example:

```bash
set CACHE_TTL_SECONDS=120
set RATE_LIMIT_REQUESTS=20
uvicorn app.main:app --reload --port 8000
```

## API

### POST /audit

Request:

```json
{
  "url": "https://example.com"
}
```

Success response (200):

```json
{
  "success": true,
  "data": {
    "url": "https://example.com/",
    "final_url": "https://example.com/",
    "status_code": 200,
    "response_time_ms": 142.37,
    "title": "Example Domain",
    "meta_description": null,
    "content_type": "text/html; charset=UTF-8",
    "is_https": true,
    "cached": false
  }
}
```

Error response (400 / 408 / 429 / 502):

```json
{
  "success": false,
  "error": {
    "code": "INVALID_URL",
    "message": "body.url: Input should be a valid URL..."
  }
}
```

Every response includes an `X-Request-ID` header.

## Project Structure

```
app/
  main.py
  routes.py
  service.py
  models.py
  cache.py
  config.py
  middleware.py
  logger.py
  utils.py
tests/
.github/workflows/ci.yml
requirements.txt
```

## Tests

```bash
pytest -q
```

## Render Deployment

- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Optional env vars: `CACHE_TTL_SECONDS`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`

## Design Decisions

- Cache TTL is read from `CACHE_TTL_SECONDS` so the cache window is configurable without code changes.
- Per-client rate limiting (incoming IP traffic) is separate from outbound concurrency limiting (how many URLs we fetch at once).
- Cache is checked before acquiring the outbound semaphore, so repeated URLs do not use a concurrency slot.
- Cache keys are lowercased and trailing slashes are stripped so casing and trailing `/` share one entry.
- Middleware assigns a UUID `request_id`, returns it as `X-Request-ID`, and includes it in access and audit logs.

## Assumptions

- Only http/https URLs are accepted.
- Redirects are followed; `final_url` is the final destination.
- Title and meta description are parsed only for HTML responses.
- Default cache TTL is 5 minutes (override with `CACHE_TTL_SECONDS`).
- Default rate limit is 30 `/audit` requests per IP per 60 seconds.
- Cache and rate-limit state are in-memory and per process.

## AI Usage

I used Cursor AI as a coding assistant to speed up development by generating boilerplate code, suggesting FastAPI patterns, and helping with repetitive implementation tasks. I also used AI to clarify concepts around asynchronous requests and caching while building the project.

Afterwards, I reviewed the generated code and made several manual improvements, including making the cache TTL configurable through environment variables, adding per-client rate limiting (separate from outbound concurrency), wiring request IDs through structured logs, normalizing cache keys, refining timeout and connection error handling, fixing the pytest configuration (`pythonpath = .`), and testing the API locally to verify the expected behavior.

AI helped accelerate development, but I manually reviewed, modified, debugged, and tested the final implementation before submission.
