#!/usr/bin/env python3
"""
tests/test_modio_retries.py
---------------------------
Unit tests for ModioClient exponential backoff, jitter, and Retry-After header parsing.
"""

import io
import json
import unittest
import urllib.error
from unittest.mock import Mock, patch

from bg3_core.modio_client import ModioClient, ModioError


class ModioClientRetriesTests(unittest.TestCase):
    def test_retry_after_http_429_recovery(self):
        token = "test-token"
        headers = {"Retry-After": "0.01"}
        error_429 = urllib.error.HTTPError(
            "https://example.invalid",
            429,
            "Too Many Requests",
            headers,  # type: ignore[arg-type]
            io.BytesIO(b"Rate limit exceeded"),
        )

        success_resp = Mock()
        success_resp.read.return_value = json.dumps({"status": "recovered"}).encode("utf-8")
        success_resp.__enter__ = Mock(return_value=success_resp)
        success_resp.__exit__ = Mock(return_value=False)

        opener = Mock(side_effect=[error_429, success_resp])
        client = ModioClient(token, opener=opener, max_retries=2, backoff_factor=0.01, jitter=False)

        with patch("time.sleep") as mock_sleep:
            result = client.request("GET", "/games/6715/mods")

        self.assertEqual(result, {"status": "recovered"})
        self.assertEqual(opener.call_count, 2)
        mock_sleep.assert_called_once_with(0.01)

    def test_retry_after_http_503_recovery(self):
        token = "test-token"
        error_503 = urllib.error.HTTPError(
            "https://example.invalid",
            503,
            "Service Unavailable",
            {},
            io.BytesIO(b"Temporary outage"),
        )

        success_resp = Mock()
        success_resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        success_resp.__enter__ = Mock(return_value=success_resp)
        success_resp.__exit__ = Mock(return_value=False)

        opener = Mock(side_effect=[error_503, success_resp])
        client = ModioClient(token, opener=opener, max_retries=3, backoff_factor=0.01, jitter=False)

        with patch("time.sleep") as mock_sleep:
            result = client.request("GET", "/games/6715/mods")

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(opener.call_count, 2)
        mock_sleep.assert_called_once_with(0.01)

    def test_retry_exhaustion_raises_modio_error_with_redaction(self):
        token = "secret-token-12345"

        def raise_error_500(*args, **kwargs):
            raise urllib.error.HTTPError(
                "https://example.invalid",
                500,
                "Internal Server Error",
                {},
                io.BytesIO(f"Internal fault with token {token}".encode("utf-8")),
            )

        opener = Mock(side_effect=raise_error_500)
        client = ModioClient(token, opener=opener, max_retries=2, backoff_factor=0.01, jitter=False)

        with patch("time.sleep"):
            with self.assertRaises(ModioError) as cm:
                client.request("GET", "/games/6715/mods")

        self.assertEqual(opener.call_count, 3)  # Initial try + 2 retries
        self.assertNotIn(token, str(cm.exception))
        self.assertIn("[REDACTED]", str(cm.exception))
        self.assertIn("HTTP 500", str(cm.exception))

    def test_non_retryable_error_fails_immediately(self):
        token = "test-token"
        error_404 = urllib.error.HTTPError(
            "https://example.invalid",
            404,
            "Not Found",
            {},
            io.BytesIO(b"Resource does not exist"),
        )

        opener = Mock(side_effect=error_404)
        client = ModioClient(token, opener=opener, max_retries=3)

        with patch("time.sleep") as mock_sleep:
            with self.assertRaises(ModioError) as cm:
                client.request("GET", "/games/6715/mods/999999")

        self.assertEqual(opener.call_count, 1)
        mock_sleep.assert_not_called()
        self.assertIn("HTTP 404", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
