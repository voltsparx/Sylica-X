import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from core.collect.http_resilience import RetryPolicy, request_text_with_retries


class _FakeResponse:
    def __init__(self, *, status: int, url: str, body: str, headers: dict[str, str] | None = None):
        self.status = status
        self.url = url
        self._body = body
        self.headers = headers or {}

    async def text(self, errors: str = "ignore") -> str:
        _ = errors
        return self._body


class _RequestContext:
    def __init__(self, outcome):
        self.outcome = outcome

    async def __aenter__(self):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    async def __aexit__(self, exc_type, exc, tb):
        _ = (exc_type, exc, tb)
        return False


class _FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        if not self.outcomes:
            raise RuntimeError("No more fake outcomes configured.")
        return _RequestContext(self.outcomes.pop(0))


class TestHttpResilience(unittest.IsolatedAsyncioTestCase):
    async def test_retry_on_429_then_success(self):
        session = _FakeSession(
            [
                _FakeResponse(
                    status=429,
                    url="https://example.com",
                    body="retry",
                    headers={"Retry-After": "0"},
                ),
                _FakeResponse(
                    status=200,
                    url="https://example.com",
                    body="ok",
                    headers={"Content-Type": "text/plain"},
                ),
            ]
        )

        with patch("core.collect.http_resilience.asyncio.sleep", new=AsyncMock()) as mocked_sleep:
            result = await request_text_with_retries(
                session,
                method="GET",
                url="https://example.com",
                retry_policy=RetryPolicy(attempts=3, base_delay_seconds=0.01, max_delay_seconds=0.05),
            )

        self.assertEqual(200, result.status_code)
        self.assertEqual("ok", result.body)
        self.assertEqual(2, result.attempts_used)
        self.assertEqual(2, len(session.calls))
        self.assertGreaterEqual(mocked_sleep.await_count, 1)

    async def test_returns_error_after_timeout_retries(self):
        session = _FakeSession([asyncio.TimeoutError(), asyncio.TimeoutError()])
        with patch("core.collect.http_resilience.asyncio.sleep", new=AsyncMock()):
            result = await request_text_with_retries(
                session,
                method="GET",
                url="https://timeout.example",
                retry_policy=RetryPolicy(attempts=2, base_delay_seconds=0.01, max_delay_seconds=0.02),
            )

        self.assertIsNone(result.status_code)
        self.assertEqual("Timeout", result.error)
        self.assertEqual(2, result.attempts_used)

    async def test_does_not_retry_non_retryable_status(self):
        session = _FakeSession([_FakeResponse(status=404, url="https://missing.example", body="missing")])
        with patch("core.collect.http_resilience.asyncio.sleep", new=AsyncMock()) as mocked_sleep:
            result = await request_text_with_retries(
                session,
                method="GET",
                url="https://missing.example",
                retry_policy=RetryPolicy(attempts=4, base_delay_seconds=0.01),
            )

        self.assertEqual(404, result.status_code)
        self.assertEqual(1, result.attempts_used)
        self.assertEqual(1, len(session.calls))
        self.assertEqual(0, mocked_sleep.await_count)


if __name__ == "__main__":
    unittest.main()


