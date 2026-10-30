#!/usr/bin/env python3
"""
tests/test_modio_client.py
--------------------------
Unit tests for scripts/lib/modio_client.py: ModioClient, pagination, auth, and error redaction.
"""

import io
import json
import unittest
import urllib.error
from unittest.mock import Mock

from bg3_core.modio_client import ModioClient, ModioError


class ModioClientTests(unittest.TestCase):
    def test_request_headers_and_bearer_auth(self):
        response = Mock()
        response.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("secret-pat", opener=opener)
        payload = client.request("GET", "/games/6715/mods")

        self.assertEqual(payload, {"status": "ok"})
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-pat")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIn("g-6715.modapi.io", request.full_url)

    def test_request_handles_full_url(self):
        response = Mock()
        response.read.return_value = b"{}"
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("pat", opener=opener)
        client.request("GET", "https://api.mod.io/v1/me/subscribed")

        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.startswith("https://api.mod.io/v1/me/subscribed"))

    def test_request_redacts_token_on_http_error(self):
        token = "super-secret-token"
        error = urllib.error.HTTPError(
            "https://example.invalid",
            401,
            "Unauthorized",
            {},
            io.BytesIO(f"failed authentication with token {token}".encode("utf-8")),
        )
        opener = Mock(side_effect=error)
        client = ModioClient(token, opener=opener)

        with self.assertRaises(ModioError) as cm:
            client.request("GET", "/me/subscribed")

        self.assertNotIn(token, str(cm.exception))
        self.assertIn("[REDACTED]", str(cm.exception))

    def test_get_paged_collects_all_pages(self):
        calls = []

        def fake_opener(req, timeout=30):
            calls.append(req.full_url)
            if "_offset=0" in req.full_url:
                body = json.dumps({
                    "data": [{"id": 1, "name": "Mod 1"}, {"id": 2, "name": "Mod 2"}],
                    "result_total": 3,
                }).encode("utf-8")
            else:
                body = json.dumps({
                    "data": [{"id": 3, "name": "Mod 3"}],
                    "result_total": 3,
                }).encode("utf-8")

            resp = Mock()
            resp.read.return_value = body
            resp.__enter__ = Mock(return_value=resp)
            resp.__exit__ = Mock(return_value=False)
            return resp

        client = ModioClient("tok", opener=fake_opener)
        items = client.get_paged("/me/subscribed", page_size=2)

        self.assertEqual(len(items), 3)
        self.assertEqual([i["id"] for i in items], [1, 2, 3])
        self.assertEqual(len(calls), 2)

    def test_get_paged_rejects_invalid_list_shape(self):
        response = Mock()
        response.read.return_value = json.dumps({"data": "not a list"}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("tok", opener=opener)
        with self.assertRaises(ModioError):
            client.get_paged("/me/subscribed")


if __name__ == "__main__":
    unittest.main()
